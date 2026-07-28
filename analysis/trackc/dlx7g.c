/* dlx7g.c — guided dancing-links Algorithm X for rooted exact cover.
 *
 * Track C engine (docs/TRACKC-DESIGN.md §5).  Descendant of
 * analysis/farm/dlx7_win.c: same instance text format, same rooted-forest
 * machinery, same exit codes (0 solution / 2 exhausted / 3 timeout).
 *
 * Instance file format (written by solve_dlx.py / solve_guided.py):
 *   ncols nrows nloops nchild
 *   then nrows lines:  loop_id parent_code c0 c1 ... c{nchild-1}
 *     parent_code = -1 if the row's parent orbit is a forest root,
 *     else the column index of the parent orbit.
 *   Row ids are line order, 0-based.
 *
 * usage:
 *   dlx7g <instance.txt> [--weights f] [--epsilon p] [--seed s]
 *         [--time-limit sec] [--max-nodes N] [--dump-features f]
 *         [--out f] [--first-only] [--progress-nodes N]
 *
 * build: cc -O2 -o dlx7g dlx7g.c -lm
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <limits.h>

#define NFEAT 8

/* ------------------------------------------------------------------ rng */
static unsigned long long rng_state = 88172645463325252ull;
static unsigned long long xrand(void){
    rng_state ^= rng_state << 13; rng_state ^= rng_state >> 7;
    rng_state ^= rng_state << 17; return rng_state;
}

#ifdef _WIN32
#include <windows.h>
static double now_s(void){
    LARGE_INTEGER f, t;
    QueryPerformanceFrequency(&f); QueryPerformanceCounter(&t);
    return (double)t.QuadPart / (double)f.QuadPart;
}
#else
static double now_s(void){
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec*1e-9;
}
#endif

/* -------------------------------------------------------------- instance */
static int ncols, nrows, nloops, nchild;
static int *row_loop, *row_parent;   /* per row */
static int *row_child;               /* nrows*nchild */
static double *static_min_child_log; /* per row, feature 7 */
static int max_col_sz;               /* max initial column size */
static int depth_bound;              /* ncols/nchild + slack */

/* dancing links arrays */
static int *L, *R, *U, *D, *C, *ROWID, *SZ;
static int head;
static int *sol; static int nsol;
static long long nodes, node_cap;
static double deadline;
static long long stat_cycle_prunes, stat_dead_ends, stat_rootless;
static int max_depth_attempt, max_depth_ever;

/* guidance */
static double W[NFEAT], Wbias;
static int have_weights = 0;
static double epsilon_p = 0.0;
static unsigned long long epsilon_thresh = 0; /* xrand() < thresh -> shuffle */

/* forest state: loop -> parent loop (or ROOTMARK) ; col -> covering row */
#define NOPAR -1
#define ROOTMARK -2
static int *parent_of;    /* per loop: NOPAR none, ROOTMARK root, else loop */
static int *covered_by;   /* per col: row id or -1 */
/* loop-level pending: per col, list of loops waiting for owner */
static int **pend; static int *npend, *cappend;

/* Track C §2 grounded / pending state (per orbit == per column) */
static unsigned char *grounded;  /* per col */
static int *pending;             /* per col: # placed-but-ungrounded rows r' with p(r')==col */
static int **pendrow; static int *npendrow, *cappendrow; /* those rows */

/* undo trail per row application */
typedef struct { int type, a, b; } Op;
/* 0 parent_of(loop)  1 covered_by(col)  2 loop-pend(col)
 * 3 grounded(col)    4 pending(col)=b   5 pendrow push(col) */
static Op *trail; static int ntrail, captrail;

static void trail_push(int type, int a, int b){
    if (ntrail >= captrail){
        captrail = captrail ? captrail*2 : 4096;
        trail = realloc(trail, (size_t)captrail*sizeof(Op));
        if (!trail){ fprintf(stderr, "OOM trail\n"); exit(1); }
    }
    trail[ntrail].type = type; trail[ntrail].a = a; trail[ntrail].b = b; ntrail++;
}

static void trail_unwind(int to){
    while (ntrail > to){
        Op *o = &trail[--ntrail];
        switch (o->type){
        case 0: parent_of[o->a] = NOPAR; break;
        case 1: covered_by[o->a] = -1; break;
        case 2: npend[o->a]--; break;
        case 3: grounded[o->a] = 0; break;
        case 4: pending[o->a] = o->b; break;
        case 5: pending[o->a]--; npendrow[o->a]--; break;
        }
    }
}

static int has_cycle_from(int lp){
    static int *seen = NULL; static int stamp = 0;
    if (!seen) seen = calloc(nloops, sizeof(int));
    stamp++;
    while (lp >= 0){
        if (seen[lp] == stamp) return 1;
        seen[lp] = stamp;
        int p = parent_of[lp];
        if (p == ROOTMARK || p == NOPAR) return 0;
        lp = p;
    }
    return 0;
}

/* ------------------------------------------ grounded/pending propagation */
static void ground_row(int rid);

static void ground_col(int c){
    if (grounded[c]) return;
    grounded[c] = 1; trail_push(3, c, 0);
    if (pending[c]){ trail_push(4, c, pending[c]); pending[c] = 0; }
    for (int t = 0; t < npendrow[c]; t++) ground_row(pendrow[c][t]);
}

static void ground_row(int rid){
    for (int k = 0; k < nchild; k++) ground_col(row_child[rid*nchild + k]);
}

/* depth in placed-row hops from orbit `c` (-1 == root) up to a root. */
static int orbit_depth(int c){
    int d = 0;
    while (c != -1){
        int r = covered_by[c];
        if (r < 0) return d;          /* ungrounded chain: caller guards */
        d++;
        if (d > nloops + 2) return d;  /* cycle guard */
        c = row_parent[r];
    }
    return d;
}

/* ------------------------------------------------------- forest push/pop */
static int forest_push(int rid, int *trail_start){
    *trail_start = ntrail;
    int lp = row_loop[rid];
    int po = row_parent[rid];
    if (po == -1){
        parent_of[lp] = ROOTMARK;
        trail_push(0, lp, 0);
    } else if (covered_by[po] >= 0){
        parent_of[lp] = row_loop[covered_by[po]];
        trail_push(0, lp, 0);
    } else {
        if (npend[po] >= cappend[po]){
            cappend[po] = cappend[po] ? cappend[po]*2 : 4;
            pend[po] = realloc(pend[po], (size_t)cappend[po]*sizeof(int));
        }
        pend[po][npend[po]++] = lp;
        trail_push(2, po, lp);
    }
    for (int k = 0; k < nchild; k++){
        int c = row_child[rid*nchild + k];
        covered_by[c] = rid;
        trail_push(1, c, 0);
        for (int t = 0; t < npend[c]; t++){
            int Wl = pend[c][t];
            parent_of[Wl] = lp;
            trail_push(0, Wl, 0);
        }
    }
    if (has_cycle_from(lp)){
        trail_unwind(*trail_start);
        return 0;
    }
    /* Track C grounded/pending update */
    if (po == -1 || grounded[po]){
        ground_row(rid);
    } else {
        if (npendrow[po] >= cappendrow[po]){
            cappendrow[po] = cappendrow[po] ? cappendrow[po]*2 : 4;
            pendrow[po] = realloc(pendrow[po], (size_t)cappendrow[po]*sizeof(int));
        }
        pendrow[po][npendrow[po]++] = rid;
        pending[po]++;
        trail_push(5, po, 0);
    }
    return 1;
}

static void forest_pop(int trail_start){ trail_unwind(trail_start); }

/* ------------------------------------------------------------ dlx cover */
static void cover(int c){
    R[L[c]] = R[c]; L[R[c]] = L[c];
    for (int i = D[c]; i != c; i = D[i])
        for (int j = R[i]; j != i; j = R[j]){
            U[D[j]] = U[j]; D[U[j]] = D[j]; SZ[C[j]]--;
        }
}
static void uncover(int c){
    for (int i = U[c]; i != c; i = U[i])
        for (int j = L[i]; j != i; j = L[j]){
            SZ[C[j]]++; U[D[j]] = j; D[U[j]] = j;
        }
    R[L[c]] = c; L[R[c]] = c;
}

/* final validation of a complete cover: rooted forest (matches check_cover) */
static int complete_ok(void){
    static int *stampv = NULL; static int stamp = 0;
    static int *path = NULL;
    if (!stampv){
        stampv = calloc(nloops, sizeof(int));
        path = calloc(nloops, sizeof(int));
    }
    stamp++;
    for (int si = 0; si < nsol; si++){
        int npath = 0;
        int lp = row_loop[sol[si]];
        while (1){
            if (stampv[lp] == stamp){
                int oncur = 0;
                for (int t = 0; t < npath; t++) if (path[t] == lp){ oncur = 1; break; }
                if (oncur) return 0;   /* cycle */
                break;                  /* previously classified ok */
            }
            stampv[lp] = stamp;
            path[npath++] = lp;
            int po = -3, found = 0;
            for (int sj = 0; sj < nsol; sj++)
                if (row_loop[sol[sj]] == lp){ po = row_parent[sol[sj]]; found = 1; break; }
            if (!found) return 0;
            if (po == -1) break;              /* root */
            if (covered_by[po] < 0) return 0; /* dangling */
            lp = row_loop[covered_by[po]];
        }
    }
    return 1;
}

/* ------------------------------------------------------------- features */
/* Feature vector per docs/TRACKC-DESIGN.md §2, LOCKED order.
 * Evaluated at the node state BEFORE the MRV column is covered. */
static void features(int rid, double *f){
    int mn = INT_MAX; double sumlog = 0.0; int scarce = 0; long pend_sum = 0;
    for (int k = 0; k < nchild; k++){
        int c = row_child[rid*nchild + k];
        int s = SZ[c];
        if (s < mn) mn = s;
        sumlog += log1p((double)s);
        if (s <= 2) scarce++;
        pend_sum += pending[c];
    }
    int po = row_parent[rid];
    int g = (po == -1) || grounded[po];
    f[0] = log1p((double)mn);
    f[1] = sumlog / (double)nchild;
    f[2] = (double)scarce / (double)nchild;
    f[3] = (po == -1) ? 1.0 : 0.0;
    f[4] = g ? 1.0 : 0.0;
    f[5] = g ? log1p((double)orbit_depth(po)) : 0.0;
    f[6] = static_min_child_log[rid];
    f[7] = (double)pend_sum / (double)nchild;
}

static double score_row(int rid){
    double f[NFEAT];
    features(rid, f);
    double s = Wbias;
    for (int k = 0; k < NFEAT; k++) s += W[k]*f[k];
    return s;
}

/* ------------------------------------------------------- candidate pools */
static int *cand_pool;      /* depth_bound * max_col_sz */
static double *score_pool;

static void sort_by_rowid(int *cands, int k){
    for (int i = 1; i < k; i++){
        int v = cands[i], rv = ROWID[v], j = i-1;
        while (j >= 0 && ROWID[cands[j]] > rv){ cands[j+1] = cands[j]; j--; }
        cands[j+1] = v;
    }
}

/* descending score, ties by ascending row id (input already rowid-ascending) */
static void sort_by_score(int *cands, double *sc, int k){
    for (int i = 1; i < k; i++){
        int v = cands[i]; double sv = sc[i]; int j = i-1;
        while (j >= 0 && sc[j] < sv){ cands[j+1] = cands[j]; sc[j+1] = sc[j]; j--; }
        cands[j+1] = v; sc[j+1] = sv;
    }
}

/* -------------------------------------------------------------- progress */
static double t_start, t_last_progress;
static long long progress_nodes = 5000000;
static long long next_progress;
static long long grand_nodes_prev;

static void maybe_progress(void){
    double t = now_s();
    if (nodes < next_progress && t - t_last_progress < 10.0) return;
    next_progress = nodes + progress_nodes;
    t_last_progress = t;
    fprintf(stderr, "[progress] nodes=%lld total=%lld depth=%d maxdepth=%d elapsed=%.1fs\n",
            nodes, grand_nodes_prev + nodes, nsol, max_depth_ever, t - t_start);
}

/* ----------------------------------------------------------------- search */
static int search(int depth){
    nodes++;
    if (nsol > max_depth_attempt){ max_depth_attempt = nsol; }
    if (nsol > max_depth_ever){ max_depth_ever = nsol; }
    if ((nodes & 65535) == 0){
        maybe_progress();
        if (now_s() > deadline) return -1;
    }
    if ((nodes & 2047) == 0 && now_s() > deadline) return -1;
    if (node_cap && nodes > node_cap) return -1;
    if (R[head] == head){
        if (complete_ok()) return 1;
        stat_rootless++;
        return 0;
    }
    int best = -1, best_sz = 1<<30;
    for (int j = R[head]; j != head; j = R[j])
        if (SZ[j] < best_sz){ best_sz = SZ[j]; best = j; }
    if (best_sz == 0){ stat_dead_ends++; return 0; }
    int c = best;

    /* collect candidates BEFORE covering c (feature state = partial cover) */
    int base = depth * max_col_sz;
    if (depth >= depth_bound){ fprintf(stderr, "depth overflow\n"); exit(1); }
    int *cands = cand_pool + base;
    double *sc = score_pool + base;
    int k = 0;
    for (int i = D[c]; i != c; i = D[i]){
        if (k >= max_col_sz){ fprintf(stderr, "cand overflow\n"); exit(1); }
        cands[k++] = i;
    }
    sort_by_rowid(cands, k);

    int shuffled = 0;
    if (epsilon_thresh){
        if (xrand() < epsilon_thresh){
            for (int i = k-1; i > 0; i--){
                int j = (int)(xrand()%(unsigned long long)(i+1));
                int t = cands[i]; cands[i] = cands[j]; cands[j] = t;
            }
            shuffled = 1;
        }
    }
    if (!shuffled && have_weights){
        for (int i = 0; i < k; i++) sc[i] = score_row(ROWID[cands[i]]);
        sort_by_score(cands, sc, k);
    }

    cover(c);
    for (int ci = 0; ci < k; ci++){
        int i = cands[ci];
        int rid = ROWID[i], ts;
        if (!forest_push(rid, &ts)){ stat_cycle_prunes++; continue; }
        sol[nsol++] = rid;
        for (int j = R[i]; j != i; j = R[j]) cover(C[j]);
        int res = search(depth+1);
        for (int j = L[i]; j != i; j = L[j]) uncover(C[j]);
        if (res == 1) return 1;
        nsol--;
        forest_pop(ts);
        if (res == -1){ uncover(c); return -1; }
    }
    uncover(c);
    return 0;
}

/* --------------------------------------------------------- dump-features */
static int dump_features(const int *cover_rows, int ncover, FILE *out){
    int nodek = 0;
    while (R[head] != head){
        int best = -1, best_sz = 1<<30;
        for (int j = R[head]; j != head; j = R[j])
            if (SZ[j] < best_sz){ best_sz = SZ[j]; best = j; }
        if (best_sz == 0){
            fprintf(stderr, "dump-features: dead end at node %d (col %d)\n", nodek, best);
            return 1;
        }
        int c = best;
        int *cands = cand_pool;
        int k = 0;
        for (int i = D[c]; i != c; i = D[i]) cands[k++] = i;
        sort_by_rowid(cands, k);
        fprintf(out, "NODE %d col=%d\n", nodek, c);
        for (int ci = 0; ci < k; ci++){
            int rid = ROWID[cands[ci]];
            double f[NFEAT];
            features(rid, f);
            fprintf(out, "%d", rid);
            for (int t = 0; t < NFEAT; t++) fprintf(out, " %.6f", f[t]);
            fprintf(out, "\n");
        }
        /* place the cover row that covers c */
        int pick = -1, picknode = -1;
        for (int ci = 0; ci < k; ci++){
            int rid = ROWID[cands[ci]];
            for (int t = 0; t < ncover; t++)
                if (cover_rows[t] == rid){ pick = rid; picknode = cands[ci]; break; }
            if (pick >= 0) break;
        }
        if (pick < 0){
            fprintf(stderr, "dump-features: no cover row covers column %d at node %d\n",
                    c, nodek);
            return 1;
        }
        cover(c);
        int ts;
        if (!forest_push(pick, &ts)){
            fprintf(stderr, "dump-features: cover row %d creates a forest cycle\n", pick);
            return 1;
        }
        sol[nsol++] = pick;
        for (int j = R[picknode]; j != picknode; j = R[j]) cover(C[j]);
        nodek++;
    }
    fprintf(stderr, "dump-features: %d nodes, %d rows placed\n", nodek, nsol);
    if (nsol != ncover)
        fprintf(stderr, "dump-features: WARNING placed %d of %d cover rows\n",
                nsol, ncover);
    return 0;
}

/* ----------------------------------------------------------- build links */
static void build_links(void){
    int total = ncols + 1 + nrows*nchild;
    if (!L){
        L = malloc((size_t)total*sizeof(int)); R = malloc((size_t)total*sizeof(int));
        U = malloc((size_t)total*sizeof(int)); D = malloc((size_t)total*sizeof(int));
        C = malloc((size_t)total*sizeof(int)); ROWID = malloc((size_t)total*sizeof(int));
        SZ = malloc((size_t)(ncols+1)*sizeof(int));
    }
    head = ncols;
    for (int i = 0; i <= ncols; i++){
        L[i] = (i + ncols) % (ncols+1);
        R[i] = (i + 1) % (ncols+1);
        U[i] = i; D[i] = i; C[i] = i; ROWID[i] = -1; SZ[i] = 0;
    }
    SZ[ncols] = 1<<30;
    int nid = ncols + 1;
    for (int rid = 0; rid < nrows; rid++){   /* ascending row id: deterministic */
        int first = -1;
        for (int k = 0; k < nchild; k++){
            int ci = row_child[rid*nchild + k];
            int id = nid++;
            U[id] = U[ci]; D[id] = ci; D[U[ci]] = id; U[ci] = id;
            C[id] = ci; ROWID[id] = rid; SZ[ci]++;
            if (first < 0){ first = id; L[id] = id; R[id] = id; }
            else { L[id] = L[first]; R[id] = first; R[L[first]] = id; L[first] = id; }
        }
    }
}

static void reset_state(void){
    for (int i = 0; i < nloops; i++) parent_of[i] = NOPAR;
    for (int i = 0; i < ncols; i++){
        covered_by[i] = -1; npend[i] = 0;
        grounded[i] = 0; pending[i] = 0; npendrow[i] = 0;
    }
    ntrail = 0; nsol = 0; nodes = 0; max_depth_attempt = 0;
    stat_cycle_prunes = stat_dead_ends = stat_rootless = 0;
}

/* ------------------------------------------------------------------ main */
static void usage(void){
    fprintf(stderr,
      "usage: dlx7g <instance.txt> [--weights f] [--epsilon p] [--seed s]\n"
      "             [--time-limit sec] [--max-nodes N] [--dump-features f]\n"
      "             [--out f] [--first-only] [--progress-nodes N]\n");
}

static int load_weights(const char *fn){
    FILE *fh = fopen(fn, "r");
    if (!fh){ fprintf(stderr, "cannot open weights file %s\n", fn); return 1; }
    char tag[64]; int nf = 0;
    if (fscanf(fh, "%63s %d", tag, &nf) != 2){
        fprintf(stderr, "bad weights header\n"); fclose(fh); return 1; }
    if (strcmp(tag, "trackc-w1") != 0 || nf != NFEAT){
        fprintf(stderr, "weights header must be 'trackc-w1 %d' (got '%s %d')\n",
                NFEAT, tag, nf);
        fclose(fh); return 1;
    }
    for (int i = 0; i < NFEAT; i++)
        if (fscanf(fh, "%lf", &W[i]) != 1){
            fprintf(stderr, "weights: need %d floats\n", NFEAT); fclose(fh); return 1; }
    if (fscanf(fh, "%lf", &Wbias) != 1){
        fprintf(stderr, "weights: missing bias\n"); fclose(fh); return 1; }
    fclose(fh);
    have_weights = 1;
    return 0;
}

int main(int argc, char **argv){
    const char *inst_fn = NULL, *w_fn = NULL, *dump_fn = NULL, *out_fn = NULL;
    double tl = 3600.0;
    long long total_cap = 0;
    unsigned long long seed = 0;
    int first_only = 1;

    if (argc < 2){ usage(); return 1; }
    for (int i = 1; i < argc; i++){
        const char *a = argv[i];
        if (a[0] != '-'){ if (!inst_fn) inst_fn = a; else { usage(); return 1; } }
        else if (!strcmp(a, "--weights") && i+1 < argc) w_fn = argv[++i];
        else if (!strcmp(a, "--epsilon") && i+1 < argc) epsilon_p = atof(argv[++i]);
        else if (!strcmp(a, "--seed") && i+1 < argc) seed = strtoull(argv[++i], NULL, 10);
        else if (!strcmp(a, "--time-limit") && i+1 < argc) tl = atof(argv[++i]);
        else if (!strcmp(a, "--max-nodes") && i+1 < argc) total_cap = atoll(argv[++i]);
        else if (!strcmp(a, "--dump-features") && i+1 < argc) dump_fn = argv[++i];
        else if (!strcmp(a, "--out") && i+1 < argc) out_fn = argv[++i];
        else if (!strcmp(a, "--progress-nodes") && i+1 < argc)
            progress_nodes = atoll(argv[++i]);
        else if (!strcmp(a, "--first-only")) first_only = 1;
        else { fprintf(stderr, "unknown option %s\n", a); usage(); return 1; }
    }
    (void)first_only;  /* the search always stops at the first solution */
    if (!inst_fn){ usage(); return 1; }
    if (epsilon_p < 0.0) epsilon_p = 0.0;
    if (epsilon_p > 1.0) epsilon_p = 1.0;
    if (epsilon_p > 0.0){
        double t = epsilon_p * 18446744073709551616.0;
        epsilon_thresh = (t >= 18446744073709551615.0) ? ULLONG_MAX
                                                       : (unsigned long long)t;
        if (epsilon_thresh == 0) epsilon_thresh = 1;
    }
    t_start = now_s();
    t_last_progress = t_start;
    deadline = t_start + tl;

    /* ------------------------------------------------------ read instance */
    FILE *fh = fopen(inst_fn, "r");
    if (!fh){ fprintf(stderr, "cannot open instance %s\n", inst_fn); return 1; }
    if (fscanf(fh, "%d %d %d %d", &ncols, &nrows, &nloops, &nchild) != 4){
        fprintf(stderr, "bad instance header\n"); return 1; }
    if (nchild < 1 || nchild > 32){ fprintf(stderr, "bad nchild %d\n", nchild); return 1; }
    row_loop = malloc((size_t)nrows*sizeof(int));
    row_parent = malloc((size_t)nrows*sizeof(int));
    row_child = malloc((size_t)nrows*nchild*sizeof(int));
    for (int i = 0; i < nrows; i++){
        if (fscanf(fh, "%d %d", &row_loop[i], &row_parent[i]) != 2){
            fprintf(stderr, "bad row %d\n", i); return 1; }
        for (int k = 0; k < nchild; k++)
            if (fscanf(fh, "%d", &row_child[i*nchild+k]) != 1){
                fprintf(stderr, "bad row %d child %d\n", i, k); return 1; }
    }
    fclose(fh);

    /* static column sizes -> feature 7 + pool sizing */
    int *colsz = calloc(ncols, sizeof(int));
    for (int i = 0; i < nrows; i++)
        for (int k = 0; k < nchild; k++){
            int c = row_child[i*nchild+k];
            if (c < 0 || c >= ncols){ fprintf(stderr, "row %d bad col %d\n", i, c); return 1; }
            colsz[c]++;
        }
    max_col_sz = 1;
    for (int c = 0; c < ncols; c++) if (colsz[c] > max_col_sz) max_col_sz = colsz[c];
    max_col_sz += 8;
    static_min_child_log = malloc((size_t)nrows*sizeof(double));
    for (int i = 0; i < nrows; i++){
        int mn = INT_MAX;
        for (int k = 0; k < nchild; k++){
            int s = colsz[row_child[i*nchild+k]];
            if (s < mn) mn = s;
        }
        static_min_child_log[i] = log1p((double)mn);
    }
    free(colsz);

    depth_bound = ncols/nchild + 16;
    sol = malloc((size_t)depth_bound*sizeof(int));
    parent_of = malloc((size_t)nloops*sizeof(int));
    covered_by = malloc((size_t)ncols*sizeof(int));
    pend = calloc(ncols, sizeof(int*));
    npend = calloc(ncols, sizeof(int));
    cappend = calloc(ncols, sizeof(int));
    grounded = calloc(ncols, 1);
    pending = calloc(ncols, sizeof(int));
    pendrow = calloc(ncols, sizeof(int*));
    npendrow = calloc(ncols, sizeof(int));
    cappendrow = calloc(ncols, sizeof(int));
    cand_pool = malloc((size_t)depth_bound*max_col_sz*sizeof(int));
    score_pool = malloc((size_t)depth_bound*max_col_sz*sizeof(double));
    trail = NULL; captrail = 0; ntrail = 0;

    if (w_fn && load_weights(w_fn)) return 1;

    fprintf(stderr, "[dlx7g] %s: cols=%d rows=%d loops=%d nchild=%d "
            "maxcolsz=%d weights=%s eps=%g seed=%llu\n",
            inst_fn, ncols, nrows, nloops, nchild, max_col_sz-8,
            have_weights ? w_fn : "none", epsilon_p, (unsigned long long)seed);

    build_links();
    reset_state();

    /* ------------------------------------------------- dump-features mode */
    if (dump_fn){
        FILE *cf = fopen(dump_fn, "r");
        if (!cf){ fprintf(stderr, "cannot open cover rows file %s\n", dump_fn); return 1; }
        int *cr = malloc((size_t)nrows*sizeof(int)); int ncr = 0, rid;
        while (fscanf(cf, "%d", &rid) == 1){
            if (rid < 0 || rid >= nrows){ fprintf(stderr, "bad row id %d\n", rid); return 1; }
            cr[ncr++] = rid;
        }
        fclose(cf);
        FILE *out = stdout;
        if (out_fn){ out = fopen(out_fn, "w");
            if (!out){ fprintf(stderr, "cannot write %s\n", out_fn); return 1; } }
        int rc = dump_features(cr, ncr, out);
        if (out != stdout) fclose(out);
        return rc ? 1 : 0;
    }

    /* ------------------------------------------------------------ search */
    long long grand_nodes = 0;
    int attempt = 0;
    /* Deterministic single pass when epsilon == 0 (no randomness to re-roll).
     * With epsilon > 0 keep the node-cap restart machinery. */
    long long attempt_cap = (epsilon_thresh ? 2000000ll : 0);
    int res = 0;
    while (1){
        attempt++;
        reset_state();
        rng_state = seed*2654435761ull + (unsigned long long)attempt*97ull + 5ull;
        if (rng_state == 0) rng_state = 88172645463325252ull;
        node_cap = (total_cap && (!attempt_cap || total_cap - grand_nodes < attempt_cap))
                   ? total_cap - grand_nodes : attempt_cap;
        grand_nodes_prev = grand_nodes;
        next_progress = progress_nodes;
        res = search(0);
        grand_nodes += nodes;
        fprintf(stderr, "[attempt %d] res=%d nodes=%lld (cap %lld) total=%lld "
                "maxdepth=%d cycle_prunes=%lld dead_ends=%lld rootless=%lld\n",
                attempt, res, nodes, node_cap, grand_nodes, max_depth_attempt,
                stat_cycle_prunes, stat_dead_ends, stat_rootless);
        if (res == 1 || res == 0) break;
        if (now_s() > deadline) break;
        if (total_cap && grand_nodes >= total_cap) break;
        if (!epsilon_thresh) break;   /* deterministic: restarting is pointless */
        attempt_cap *= 2;
        if (attempt_cap > 200000000ll) attempt_cap = 200000000ll;
    }

    double el = now_s() - t_start;
    if (res == 1){
        FILE *out = stdout;
        if (out_fn){ out = fopen(out_fn, "w");
            if (!out){ fprintf(stderr, "cannot write %s\n", out_fn); return 1; } }
        for (int i = 0; i < nsol; i++) fprintf(out, "%d\n", sol[i]);
        if (out != stdout) fclose(out);
        fprintf(stderr, "RESULT SOLVED rows=%d nodes=%lld attempts=%d "
                "maxdepth=%d elapsed=%.3fs\n", nsol, grand_nodes, attempt,
                max_depth_ever, el);
        return 0;
    }
    if (res == 0){
        fprintf(stderr, "RESULT EXHAUSTED nodes=%lld attempts=%d maxdepth=%d "
                "elapsed=%.3fs\n", grand_nodes, attempt, max_depth_ever, el);
        return 2;
    }
    fprintf(stderr, "RESULT TIMEOUT nodes=%lld attempts=%d maxdepth=%d "
            "elapsed=%.3fs\n", grand_nodes, attempt, max_depth_ever, el);
    return 3;
}
