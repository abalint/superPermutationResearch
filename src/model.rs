//! Learned value-function models (phase 2), loaded from JSON files
//! produced by the Python training side (`ml/`).
//!
//! Two kinds are supported:
//!
//! * `"linear"` — `predict(x) = coef · x + bias`;
//! * `"mlp"` — standardize `x` to `(x − x_mean) / x_std`, then apply
//!   dense layers in order (`w` is row-major `[out][in]`, activation
//!   `"relu"` or `"identity"`); the final layer outputs a single scalar.
//!
//! The output is the predicted *cost-to-go* (characters still needed),
//! or — for models exported with `"target": "residual"` — the predicted
//! *residual* above the arc bound (`cost_to_go − lb_arc`); the scorer
//! adds `lb_arc` back (see [`Target`]).
//!
//! # Feature-contract versioning (append-only, length-dispatched)
//!
//! The feature contract grows append-only: [`FEATURE_ORDER_V2`] is
//! [`FEATURE_ORDER`] (the original 8) plus the phase-3
//! deficit-distribution features. A model file must declare
//! `feature_order` exactly equal to one of the two lists, and it
//! consumes exactly the first `n_features()` entries of the full
//! feature vector the scorers compute — so an old 8-feature model fed
//! the 11-feature vector produces bit-identical predictions to the
//! pre-phase-3 build (same multiplies, same accumulation order), while
//! new models see the appended features. Unknown kinds, targets,
//! activations, unrecognized feature orders, or inconsistent layer
//! shapes are rejected with a clear error.

use std::fs;
use std::path::Path;

use serde::Deserialize;

/// The original (phase-2) feature vector prefix, matching the beam's
/// O(1) child-feature computation (see `score_move`). Models declaring
/// exactly this order use only the first 8 features.
pub const FEATURE_ORDER: [&str; 8] = [
    "r",
    "cycles_remaining",
    "intact_cycles",
    "current_cycle_remaining",
    "arcs",
    "succ1_unvisited",
    "lb_cycle",
    "lb_arc",
];

/// The full (phase-3 item 3) feature vector: [`FEATURE_ORDER`] plus the
/// deficit-distribution features, in this exact order. Append-only —
/// never reorder or insert in the middle, only push to the end (and add
/// the next version constant).
pub const FEATURE_ORDER_V2: [&str; 11] = [
    "r",
    "cycles_remaining",
    "intact_cycles",
    "current_cycle_remaining",
    "arcs",
    "succ1_unvisited",
    "lb_cycle",
    "lb_arc",
    "half_open",
    "nearly_done",
    "w2_bridges",
];

/// What quantity the model was trained to predict (`"target"` in the
/// file; absent means [`Target::Absolute`], so pre-residual model files
/// load unchanged).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default, Deserialize)]
pub enum Target {
    /// Raw `cost_to_go`.
    #[default]
    #[serde(rename = "absolute")]
    Absolute,
    /// `cost_to_go − lb_arc`; the scorer must add `lb_arc` back.
    #[serde(rename = "residual")]
    Residual,
}

/// Activation function of an MLP layer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Act {
    /// `max(0, z)`.
    Relu,
    /// `z` unchanged (typically the output layer).
    Identity,
}

/// One dense MLP layer: `out = act(w · in + b)`.
#[derive(Debug, Clone, PartialEq)]
pub struct Layer {
    /// Row-major weights, `w[out][in]`.
    pub w: Vec<Vec<f64>>,
    /// Biases, one per output.
    pub b: Vec<f64>,
    /// Activation applied elementwise.
    pub act: Act,
}

/// A learned cost-to-go predictor over a prefix of the append-only
/// feature contract ([`FEATURE_ORDER`] or [`FEATURE_ORDER_V2`]); the
/// prefix length is `coef.len()` / `x_mean.len()` (see
/// [`Model::n_features`]).
#[derive(Debug, Clone, PartialEq)]
pub enum Model {
    /// `coef · x[..coef.len()] + bias`.
    Linear {
        /// Symbol count the model was trained for.
        n: usize,
        /// One coefficient per feature, in declared feature order
        /// (a prefix of [`FEATURE_ORDER_V2`]; 8 or 11 entries).
        coef: Vec<f64>,
        /// Intercept.
        bias: f64,
        /// What quantity the prediction is (see [`Target`]).
        target: Target,
    },
    /// Standardize then apply dense layers in order.
    Mlp {
        /// Symbol count the model was trained for.
        n: usize,
        /// Per-feature mean subtracted before the first layer (one per
        /// consumed feature; 8 or 11 entries).
        x_mean: Vec<f64>,
        /// Per-feature scale divided out before the first layer.
        x_std: Vec<f64>,
        /// Dense layers; the last outputs a single scalar.
        layers: Vec<Layer>,
        /// What quantity the prediction is (see [`Target`]).
        target: Target,
    },
}

/// Serde mirror of the on-disk JSON (validated into [`Model`]).
#[derive(Deserialize)]
#[serde(tag = "kind")]
enum RawModel {
    #[serde(rename = "linear")]
    Linear {
        n: usize,
        feature_order: Vec<String>,
        coef: Vec<f64>,
        bias: f64,
        #[serde(default)]
        target: Target,
    },
    #[serde(rename = "mlp")]
    Mlp {
        n: usize,
        feature_order: Vec<String>,
        x_mean: Vec<f64>,
        x_std: Vec<f64>,
        layers: Vec<RawLayer>,
        #[serde(default)]
        target: Target,
    },
}

#[derive(Deserialize)]
struct RawLayer {
    w: Vec<Vec<f64>>,
    b: Vec<f64>,
    act: String,
}

/// Validate the declared feature order against the append-only contract
/// and return the number of consumed features (8 for [`FEATURE_ORDER`],
/// 11 for [`FEATURE_ORDER_V2`]).
fn check_feature_order(fo: &[String]) -> Result<usize, String> {
    let matches =
        |names: &[&str]| fo.len() == names.len() && fo.iter().zip(names).all(|(a, b)| a == b);
    if matches(&FEATURE_ORDER) || matches(&FEATURE_ORDER_V2) {
        Ok(fo.len())
    } else {
        Err(format!(
            "feature_order must be exactly {FEATURE_ORDER:?} (v1) or {FEATURE_ORDER_V2:?} (v2), got {fo:?}"
        ))
    }
}

fn check_len(v: Vec<f64>, dim: usize, name: &str) -> Result<Vec<f64>, String> {
    if v.len() == dim {
        Ok(v)
    } else {
        Err(format!(
            "{name} must have exactly {dim} entries (one per declared feature), got {}",
            v.len()
        ))
    }
}

impl Model {
    /// Parse and validate a model from its JSON text.
    pub fn from_json(text: &str) -> Result<Model, String> {
        let raw: RawModel =
            serde_json::from_str(text).map_err(|e| format!("invalid model JSON: {e}"))?;
        match raw {
            RawModel::Linear {
                n,
                feature_order,
                coef,
                bias,
                target,
            } => {
                let dim = check_feature_order(&feature_order)?;
                Ok(Model::Linear {
                    n,
                    coef: check_len(coef, dim, "coef")?,
                    bias,
                    target,
                })
            }
            RawModel::Mlp {
                n,
                feature_order,
                x_mean,
                x_std,
                layers,
                target,
            } => {
                let nfeat = check_feature_order(&feature_order)?;
                let x_mean = check_len(x_mean, nfeat, "x_mean")?;
                let x_std = check_len(x_std, nfeat, "x_std")?;
                if x_std.contains(&0.0) {
                    return Err("x_std entries must be nonzero".to_string());
                }
                if layers.is_empty() {
                    return Err("mlp must have at least one layer".to_string());
                }
                let mut dim = nfeat;
                let mut out = Vec::with_capacity(layers.len());
                for (i, l) in layers.into_iter().enumerate() {
                    let act = match l.act.as_str() {
                        "relu" => Act::Relu,
                        "identity" => Act::Identity,
                        other => {
                            return Err(format!(
                            "layer {i}: unknown act {other:?} (expected \"relu\" or \"identity\")"
                        ))
                        }
                    };
                    if l.w.is_empty() {
                        return Err(format!("layer {i}: w must have at least one row"));
                    }
                    if l.b.len() != l.w.len() {
                        return Err(format!(
                            "layer {i}: b has {} entries but w has {} rows",
                            l.b.len(),
                            l.w.len()
                        ));
                    }
                    for (j, row) in l.w.iter().enumerate() {
                        if row.len() != dim {
                            return Err(format!(
                                "layer {i}: w row {j} has {} entries, expected {dim}",
                                row.len()
                            ));
                        }
                    }
                    dim = l.w.len();
                    out.push(Layer {
                        w: l.w,
                        b: l.b,
                        act,
                    });
                }
                if dim != 1 {
                    return Err(format!(
                        "final layer must output exactly 1 value, got {dim}"
                    ));
                }
                Ok(Model::Mlp {
                    n,
                    x_mean,
                    x_std,
                    layers: out,
                    target,
                })
            }
        }
    }

    /// Load and validate a model from a JSON file.
    pub fn load(path: impl AsRef<Path>) -> Result<Model, String> {
        let path = path.as_ref();
        let text =
            fs::read_to_string(path).map_err(|e| format!("cannot read {}: {e}", path.display()))?;
        Model::from_json(&text)
    }

    /// Number of features the model consumes — the length of its
    /// declared `feature_order` (8 for a [`FEATURE_ORDER`] model, 11
    /// for [`FEATURE_ORDER_V2`]). Scorers pass the full current feature
    /// vector; the model reads only this prefix.
    pub fn n_features(&self) -> usize {
        match self {
            Model::Linear { coef, .. } => coef.len(),
            Model::Mlp { x_mean, .. } => x_mean.len(),
        }
    }

    /// Predicted cost-to-go for a feature vector whose prefix follows
    /// the append-only contract ([`FEATURE_ORDER_V2`]); only the first
    /// [`Model::n_features`] entries are read, in declaration order, so
    /// an 8-feature model scores bit-identically to the pre-phase-3
    /// build. `x.len()` must be at least [`Model::n_features`].
    pub fn predict(&self, x: &[f64]) -> f64 {
        assert!(
            x.len() >= self.n_features(),
            "feature vector has {} entries but the model consumes {}",
            x.len(),
            self.n_features()
        );
        match self {
            Model::Linear { coef, bias, .. } => {
                coef.iter().zip(x).map(|(c, v)| c * v).sum::<f64>() + bias
            }
            Model::Mlp {
                x_mean,
                x_std,
                layers,
                ..
            } => {
                let mut cur: Vec<f64> = x
                    .iter()
                    .zip(x_mean)
                    .zip(x_std)
                    .map(|((v, m), s)| (v - m) / s)
                    .collect();
                for layer in layers {
                    cur = layer
                        .w
                        .iter()
                        .zip(&layer.b)
                        .map(|(row, &b)| {
                            let z = row.iter().zip(&cur).map(|(w, v)| w * v).sum::<f64>() + b;
                            match layer.act {
                                Act::Relu => z.max(0.0),
                                Act::Identity => z,
                            }
                        })
                        .collect();
                }
                debug_assert_eq!(cur.len(), 1);
                cur[0]
            }
        }
    }

    /// Symbol count the model was trained for (`"n"` in the file).
    pub fn n(&self) -> usize {
        match self {
            Model::Linear { n, .. } | Model::Mlp { n, .. } => *n,
        }
    }

    /// Model kind as it appears in the JSON (`"linear"` or `"mlp"`).
    pub fn kind(&self) -> &'static str {
        match self {
            Model::Linear { .. } => "linear",
            Model::Mlp { .. } => "mlp",
        }
    }

    /// What quantity the model predicts (`"target"` in the file; absent
    /// means [`Target::Absolute`]).
    pub fn target(&self) -> Target {
        match self {
            Model::Linear { target, .. } | Model::Mlp { target, .. } => *target,
        }
    }

    /// Whether the prediction is a residual above `lb_arc` (the scorer
    /// must add `lb_arc` back).
    pub fn is_residual(&self) -> bool {
        self.target() == Target::Residual
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const FO: &str = r#"["r","cycles_remaining","intact_cycles","current_cycle_remaining","arcs","succ1_unvisited","lb_cycle","lb_arc"]"#;

    #[test]
    fn linear_round_trip_and_predict() {
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{FO},
                "coef":[1.0,0.0,0.0,0.0,0.0,0.0,0.0,2.0],"bias":1.5}}"#
        );
        let path = std::env::temp_dir().join(format!(
            "superperm_model_linear_{}.json",
            std::process::id()
        ));
        fs::write(&path, &json).unwrap();
        let m = Model::load(&path).unwrap();
        fs::remove_file(&path).ok();
        assert_eq!(m.n(), 6);
        assert_eq!(m.kind(), "linear");
        // No "target" field: old files load as absolute.
        assert_eq!(m.target(), Target::Absolute);
        assert!(!m.is_residual());
        // 1*3 + 2*10 + 1.5 = 24.5
        let x = [3.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 10.0];
        assert_eq!(m.predict(&x), 24.5);
    }

    #[test]
    fn target_field_parses_and_rejects_unknown() {
        let base = format!(r#""n":6,"feature_order":{FO},"coef":[0,0,0,0,0,0,0,0],"bias":0"#);
        let m = Model::from_json(&format!(
            r#"{{"kind":"linear","target":"residual",{base}}}"#
        ))
        .unwrap();
        assert_eq!(m.target(), Target::Residual);
        assert!(m.is_residual());
        let m = Model::from_json(&format!(
            r#"{{"kind":"linear","target":"absolute",{base}}}"#
        ))
        .unwrap();
        assert!(!m.is_residual());
        let err = Model::from_json(&format!(r#"{{"kind":"linear","target":"delta",{base}}}"#))
            .unwrap_err();
        assert!(err.contains("delta"), "{err}");
    }

    #[test]
    fn mlp_round_trip_and_forward_pass() {
        // Standardize with mean 1, std 2 on the first feature (rest
        // identity), then:
        //   layer 1 (relu):    h = relu([x0' + 0.5, -x1 + 0.25])
        //   layer 2 (identity): y = 2*h0 + 3*h1 + 0.125
        let json = format!(
            r#"{{"kind":"mlp","n":5,"feature_order":{FO},
                "x_mean":[1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
                "x_std":[2.0,1.0,1.0,1.0,1.0,1.0,1.0,1.0],
                "layers":[
                  {{"w":[[1.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0],
                         [0.0,-1.0,0.0,0.0,0.0,0.0,0.0,0.0]],
                    "b":[0.5,0.25],"act":"relu"}},
                  {{"w":[[2.0,3.0]],"b":[0.125],"act":"identity"}}
                ]}}"#
        );
        let path =
            std::env::temp_dir().join(format!("superperm_model_mlp_{}.json", std::process::id()));
        fs::write(&path, &json).unwrap();
        let m = Model::load(&path).unwrap();
        fs::remove_file(&path).ok();
        assert_eq!(m.n(), 5);
        assert_eq!(m.kind(), "mlp");
        // x = [3, 2, ...]: x0' = (3-1)/2 = 1 -> h = relu([1.5, -1.75])
        //   = [1.5, 0] -> y = 2*1.5 + 0 + 0.125 = 3.125.
        let x = [3.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        assert_eq!(m.predict(&x), 3.125);
        // x = [1, -2, ...]: x0' = 0 -> h = relu([0.5, 2.25]) ->
        //   y = 1.0 + 6.75 + 0.125 = 7.875.
        let x = [1.0, -2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0];
        assert_eq!(m.predict(&x), 7.875);
    }

    const FO_V2: &str = r#"["r","cycles_remaining","intact_cycles","current_cycle_remaining","arcs","succ1_unvisited","lb_cycle","lb_arc","half_open","nearly_done","w2_bridges"]"#;

    #[test]
    fn v2_linear_parses_and_uses_all_11_features() {
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{FO_V2},
                "coef":[0,0,0,0,0,0,0,0,1.0,10.0,100.0],"bias":0.5}}"#
        );
        let m = Model::from_json(&json).unwrap();
        assert_eq!(m.n_features(), 11);
        let x = [9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 2.0, 3.0, 4.0];
        // 1*2 + 10*3 + 100*4 + 0.5 = 432.5
        assert_eq!(m.predict(&x), 432.5);
    }

    #[test]
    fn v1_model_ignores_appended_features() {
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{FO},
                "coef":[1.0,0.0,0.0,0.0,0.0,0.0,0.0,2.0],"bias":1.5}}"#
        );
        let m = Model::from_json(&json).unwrap();
        assert_eq!(m.n_features(), 8);
        let x8 = [3.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 10.0];
        let x11 = [3.0, 9.0, 9.0, 9.0, 9.0, 9.0, 9.0, 10.0, 7.0, 7.0, 7.0];
        assert_eq!(m.predict(&x8), 24.5);
        assert_eq!(m.predict(&x11), 24.5);
    }

    #[test]
    fn rejects_coef_length_mismatched_with_feature_order() {
        // 11 coefficients under the v1 order.
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{FO},
                "coef":[0,0,0,0,0,0,0,0,0,0,0],"bias":0}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("coef"));
        // 8 coefficients under the v2 order.
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{FO_V2},
                "coef":[0,0,0,0,0,0,0,0],"bias":0}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("coef"));
    }

    #[test]
    fn rejects_partial_or_reordered_v2_feature_order() {
        // 9 features (a strict prefix between v1 and v2) is not a
        // recognized contract version.
        let fo9 = FO_V2.replace(r#","nearly_done","w2_bridges""#, "");
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{fo9},
                "coef":[0,0,0,0,0,0,0,0,0],"bias":0}}"#
        );
        assert!(Model::from_json(&json)
            .unwrap_err()
            .contains("feature_order"));
        // v2 names in the wrong order.
        let swapped = FO_V2.replace(
            r#""nearly_done","w2_bridges""#,
            r#""w2_bridges","nearly_done""#,
        );
        let json = format!(
            r#"{{"kind":"linear","n":6,"feature_order":{swapped},
                "coef":[0,0,0,0,0,0,0,0,0,0,0],"bias":0}}"#
        );
        assert!(Model::from_json(&json)
            .unwrap_err()
            .contains("feature_order"));
    }

    #[test]
    fn v2_mlp_parses_and_first_layer_width_must_match() {
        let json = format!(
            r#"{{"kind":"mlp","n":6,"feature_order":{FO_V2},
                "x_mean":[0,0,0,0,0,0,0,0,0,0,0],"x_std":[1,1,1,1,1,1,1,1,1,1,1],
                "layers":[{{"w":[[0,0,0,0,0,0,0,0,0,0,2.0]],"b":[0.25],"act":"identity"}}]}}"#
        );
        let m = Model::from_json(&json).unwrap();
        assert_eq!(m.n_features(), 11);
        let x = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 3.0];
        assert_eq!(m.predict(&x), 6.25);
        // An 8-wide first layer under the v2 order must be rejected.
        let json = format!(
            r#"{{"kind":"mlp","n":6,"feature_order":{FO_V2},
                "x_mean":[0,0,0,0,0,0,0,0,0,0,0],"x_std":[1,1,1,1,1,1,1,1,1,1,1],
                "layers":[{{"w":[[0,0,0,0,0,0,0,0]],"b":[0],"act":"identity"}}]}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("row"));
    }

    #[test]
    fn rejects_unknown_kind() {
        let json = format!(
            r#"{{"kind":"forest","n":6,"feature_order":{FO},"coef":[0,0,0,0,0,0,0,0],"bias":0}}"#
        );
        let err = Model::from_json(&json).unwrap_err();
        assert!(err.contains("forest"), "{err}");
    }

    #[test]
    fn rejects_wrong_feature_order() {
        let json = r#"{"kind":"linear","n":6,
            "feature_order":["r","cycles_remaining","intact_cycles","current_cycle_remaining","arcs","succ1_unvisited","lb_arc","lb_cycle"],
            "coef":[0,0,0,0,0,0,0,0],"bias":0}"#;
        let err = Model::from_json(json).unwrap_err();
        assert!(err.contains("feature_order"), "{err}");
    }

    #[test]
    fn rejects_bad_shapes_and_acts() {
        // Wrong coef length.
        let json =
            format!(r#"{{"kind":"linear","n":6,"feature_order":{FO},"coef":[0,0,0],"bias":0}}"#);
        assert!(Model::from_json(&json).unwrap_err().contains("coef"));
        // Unknown activation.
        let json = format!(
            r#"{{"kind":"mlp","n":6,"feature_order":{FO},
                "x_mean":[0,0,0,0,0,0,0,0],"x_std":[1,1,1,1,1,1,1,1],
                "layers":[{{"w":[[0,0,0,0,0,0,0,0]],"b":[0],"act":"tanh"}}]}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("tanh"));
        // Final layer must be scalar.
        let json = format!(
            r#"{{"kind":"mlp","n":6,"feature_order":{FO},
                "x_mean":[0,0,0,0,0,0,0,0],"x_std":[1,1,1,1,1,1,1,1],
                "layers":[{{"w":[[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]],"b":[0,0],"act":"identity"}}]}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("final layer"));
        // Row width must match the incoming dimension.
        let json = format!(
            r#"{{"kind":"mlp","n":6,"feature_order":{FO},
                "x_mean":[0,0,0,0,0,0,0,0],"x_std":[1,1,1,1,1,1,1,1],
                "layers":[{{"w":[[0,0]],"b":[0],"act":"identity"}}]}}"#
        );
        assert!(Model::from_json(&json).unwrap_err().contains("row"));
    }
}
