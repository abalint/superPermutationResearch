/* dlx7.c — dancing-links Algorithm X with incremental rooted-forest pruning,
 * randomized restarts with node caps (port of gain1.py's DLX engine to C).
 *
 * stdin instance format:
 *   ncols nrows nloops Q
 *   then nrows lines:  loop_id parent_code c0 c1 ... c{Q-1}
 *     parent_code = -1 if the row's parent orbit is a forest root,
 *     else the column index of the parent orbit.
 * usage: ./dlx7 seed time_limit_s track_forest(0/1) [max_total_nodes]
 * stdout: "SOLVED\n" + chosen row ids, or "EXHAUSTED" or "TIMEOUT".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static unsigned long long rng_state;
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

static int ncols, nrows, nloops, Q;
static int *row_loop, *row_parent;   /* per row */
static int *row_child;               /* nrows*Q */

/* dancing links arrays */
static int *L, *R, *U, *D, *C, *ROWID, *SZ;
static int head, nnodes_total;
static int *sol; static int nsol;
static long long nodes, node_cap;
static double deadline;
static int track_forest;
static long long stat_cycle_prunes, stat_dead_ends, stat_rootless;
static unsigned char *pref; static int npref; static int pref_eps = 3;

/* forest state: loop -> parent loop (or ROOTMARK) ; col -> covering row */
#define NOPAR -1
#define ROOTMARK -2
static int *parent_of;    /* per loop: NOPAR none, ROOTMARK root, else loop */
static int *covered_by;   /* per col: row id or -1 */
/* pending: per col, list of loops waiting for owner */
static int **pend; static int *npend, *cappend;

/* undo trail per row application */
typedef struct { int type, a, b; } Op;  /* 0 parent(loop), 1 covered(col), 2 pending(col,loop) */
static Op *trail; static int ntrail;

static int has_cycle_from(int lp){
    /* follow parent chain, detect revisit */
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

static int forest_push(int rid, int *trail_start){
    *trail_start = ntrail;
    if (!track_forest) return 1;
    int lp = row_loop[rid];
    int po = row_parent[rid];
    if (po == -1){
        parent_of[lp] = ROOTMARK;
        trail[ntrail].type = 0; trail[ntrail].a = lp; ntrail++;
    } else if (covered_by[po] >= 0){
        parent_of[lp] = row_loop[covered_by[po]];
        trail[ntrail].type = 0; trail[ntrail].a = lp; ntrail++;
    } else {
        if (npend[po] >= cappend[po]){
            cappend[po] = cappend[po] ? cappend[po]*2 : 4;
            pend[po] = realloc(pend[po], cappend[po]*sizeof(int));
        }
        pend[po][npend[po]++] = lp;
        trail[ntrail].type = 2; trail[ntrail].a = po; trail[ntrail].b = lp; ntrail++;
    }
    for (int k = 0; k < Q; k++){
        int c = row_child[rid*Q + k];
        covered_by[c] = rid;
        trail[ntrail].type = 1; trail[ntrail].a = c; ntrail++;
        for (int t = 0; t < npend[c]; t++){
            int W = pend[c][t];
            parent_of[W] = lp;
            trail[ntrail].type = 0; trail[ntrail].a = W; ntrail++;
        }
    }
    if (has_cycle_from(lp)){
        /* pop */
        while (ntrail > *trail_start){
            Op *o = &trail[--ntrail];
            if (o->type == 0) parent_of[o->a] = NOPAR;
            else if (o->type == 1) covered_by[o->a] = -1;
            else npend[o->a]--;
        }
        return 0;
    }
    return 1;
}

static void forest_pop(int trail_start){
    while (ntrail > trail_start){
        Op *o = &trail[--ntrail];
        if (o->type == 0) parent_of[o->a] = NOPAR;
        else if (o->type == 1) covered_by[o->a] = -1;
        else npend[o->a]--;
    }
}

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
    if (!track_forest) return 1;
    /* owner map is covered_by; walk parent chains */
    static int *state = NULL; static int *stampv = NULL; static int stamp = 0;
    static int *path = NULL;
    if (!state){
        state = calloc(nloops, sizeof(int));
        stampv = calloc(nloops, sizeof(int));
        path = calloc(nloops, sizeof(int));
    }
    stamp++;
    for (int si = 0; si < nsol; si++){
        int npath = 0;
        int lp = row_loop[sol[si]];
        while (1){
            if (stampv[lp] == stamp){
                /* already classified or on current path? */
                int oncur = 0;
                for (int t = 0; t < npath; t++) if (path[t] == lp){ oncur = 1; break; }
                if (oncur) return 0;   /* cycle */
                break;                  /* previously classified ok */
            }
            stampv[lp] = stamp;
            path[npath++] = lp;
            /* find the chosen row of loop lp: parent orbit */
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

static int search(void){
    nodes++;
    if ((nodes & 2047) == 0 && now_s() > deadline) return -1; /* timeout */
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
    cover(c);
    /* collect candidates: preferred (seed) rows first, each group shuffled */
    int cands[1024], k = 0;
    for (int i = D[c]; i != c; i = D[i]) cands[k++] = i;
    for (int i = k-1; i > 0; i--){
        int j = (int)(xrand()%(i+1)); int t = cands[i]; cands[i]=cands[j]; cands[j]=t;
    }
    if (npref){
        int tmp[1024], flag[1024], m = 0;
        for (int i = 0; i < k; i++)
            flag[i] = pref[ROWID[cands[i]]] && (int)(xrand()%100) >= pref_eps;
        for (int i = 0; i < k; i++) if (flag[i]) tmp[m++] = cands[i];
        for (int i = 0; i < k; i++) if (!flag[i]) tmp[m++] = cands[i];
        memcpy(cands, tmp, k*sizeof(int));
    }
    for (int ci = 0; ci < k; ci++){
        int i = cands[ci];
        int rid = ROWID[i], ts;
        if (!forest_push(rid, &ts)){ stat_cycle_prunes++; continue; }
        sol[nsol++] = rid;
        for (int j = R[i]; j != i; j = R[j]) cover(C[j]);
        int res = search();
        for (int j = L[i]; j != i; j = L[j]) uncover(C[j]);
        if (res == 1) return 1;
        nsol--;
        forest_pop(ts);
        if (res == -1){ uncover(c); return -1; }
    }
    uncover(c);
    return 0;
}

static void build_links(unsigned long long shuffle_seed){
    int total = ncols + 1 + nrows*Q;
    if (!L){
        L = malloc(total*sizeof(int)); R = malloc(total*sizeof(int));
        U = malloc(total*sizeof(int)); D = malloc(total*sizeof(int));
        C = malloc(total*sizeof(int)); ROWID = malloc(total*sizeof(int));
        SZ = malloc((ncols+1)*sizeof(int));
    }
    head = ncols;
    for (int i = 0; i <= ncols; i++){
        L[i] = (i + ncols) % (ncols+1);
        R[i] = (i + 1) % (ncols+1);
        U[i] = i; D[i] = i; C[i] = i; ROWID[i] = -1; SZ[i] = 0;
    }
    SZ[ncols] = 1<<30;
    int nid = ncols + 1;
    /* row insertion order shuffled */
    static int *order = NULL;
    if (!order) order = malloc(nrows*sizeof(int));
    for (int i = 0; i < nrows; i++) order[i] = i;
    rng_state = shuffle_seed;
    for (int i = nrows-1; i > 0; i--){
        int j = (int)(xrand()%(i+1)); int t = order[i]; order[i]=order[j]; order[j]=t;
    }
    for (int oi = 0; oi < nrows; oi++){
        int rid = order[oi];
        int first = -1;
        for (int k = 0; k < Q; k++){
            int ci = row_child[rid*Q + k];
            int id = nid++;
            U[id] = U[ci]; D[id] = ci; D[U[ci]] = id; U[ci] = id;
            C[id] = ci; ROWID[id] = rid; SZ[ci]++;
            if (first < 0){ first = id; L[id] = id; R[id] = id; }
            else { L[id] = L[first]; R[id] = first; R[L[first]] = id; L[first] = id; }
        }
    }
    nnodes_total = nid;
}

int main(int argc, char **argv){
    if (argc < 4){
        fprintf(stderr, "usage: dlx7 seed tl track_forest [max_total_nodes]\n");
        return 1;
    }
    long seed = atol(argv[1]);
    double tl = atof(argv[2]);
    track_forest = atoi(argv[3]);
    long long total_cap = argc > 4 ? atoll(argv[4]) : 0;
    const char *pref_fn = argc > 5 ? argv[5] : NULL;
    if (argc > 6) pref_eps = atoi(argv[6]);
    long long fixed_cap = argc > 7 ? atoll(argv[7]) : 0;
    deadline = now_s() + tl;

    if (scanf("%d %d %d %d", &ncols, &nrows, &nloops, &Q) != 4) return 1;
    row_loop = malloc(nrows*sizeof(int));
    row_parent = malloc(nrows*sizeof(int));
    row_child = malloc((size_t)nrows*Q*sizeof(int));
    for (int i = 0; i < nrows; i++){
        if (scanf("%d %d", &row_loop[i], &row_parent[i]) != 2) return 1;
        for (int k = 0; k < Q; k++)
            if (scanf("%d", &row_child[i*Q+k]) != 1) return 1;
    }
    pref = calloc(nrows, 1); npref = 0;
    if (pref_fn){
        FILE *pf = fopen(pref_fn, "r");
        if (!pf){ fprintf(stderr, "cannot open pref file\n"); return 1; }
        int rid;
        while (fscanf(pf, "%d", &rid) == 1)
            if (rid >= 0 && rid < nrows && !pref[rid]){ pref[rid] = 1; npref++; }
        fclose(pf);
        fprintf(stderr, "pref rows: %d (eps %d%%)\n", npref, pref_eps);
    }
    sol = malloc((ncols/Q + 8)*sizeof(int));
    parent_of = malloc(nloops*sizeof(int));
    covered_by = malloc(ncols*sizeof(int));
    pend = calloc(ncols, sizeof(int*));
    npend = calloc(ncols, sizeof(int));
    cappend = calloc(ncols, sizeof(int));
    trail = malloc((size_t)(ncols/Q + 8)*(Q+4)*sizeof(Op)*4);

    long long attempt_cap = fixed_cap ? fixed_cap : (npref ? 50000 : 2000000);
    long long grand_nodes = 0;
    int attempt = 0;
    while (now_s() < deadline){
        attempt++;
        build_links((unsigned long long)seed*1000003ull + attempt*7919ull + 1);
        rng_state = (unsigned long long)seed*2654435761ull + attempt*97ull + 5;
        for (int i = 0; i < nloops; i++) parent_of[i] = NOPAR;
        for (int i = 0; i < ncols; i++){ covered_by[i] = -1; npend[i] = 0; }
        ntrail = 0; nsol = 0; nodes = 0;
        stat_cycle_prunes = stat_dead_ends = stat_rootless = 0;
        node_cap = attempt_cap;
        int res = search();
        grand_nodes += nodes;
        if (res != -1 || !fixed_cap || attempt % 200 == 0)
            fprintf(stderr,
                "attempt %d: res=%d nodes=%lld (cap %lld) cycle_prunes=%lld "
                "dead_ends=%lld rootless=%lld total_nodes=%lld\n",
                attempt, res, nodes, node_cap, stat_cycle_prunes,
                stat_dead_ends, stat_rootless, grand_nodes);
        if (res == 1){
            printf("SOLVED\n");
            for (int i = 0; i < nsol; i++) printf("%d\n", sol[i]);
            return 0;
        }
        if (res == 0){
            printf("EXHAUSTED\n");
            return 2;
        }
        if (now_s() > deadline) break;
        if (total_cap && grand_nodes > total_cap) break;
        if (!fixed_cap){
            attempt_cap = attempt_cap * 2;
            if (attempt_cap > 200000000ll) attempt_cap = 200000000ll;
        }
    }
    printf("TIMEOUT\n");
    return 3;
}
