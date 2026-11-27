/* brute.c — abc389_g full enumeration truth generator.
 *
 * Counts, for each M = n-1 .. n(n-1)/2, the number of connected simple
 * labeled graphs on vertices {0..n-1} in which the number of vertices at
 * even BFS-distance from vertex 0 equals the number at odd distance
 * (vertex 0 itself counts as even side).
 *
 * Usage: ./brute n        -> prints n(n-1)/2 - (n-1) + 1 integers:
 *                             counts[M] for M = n-1 .. E  (space separated).
 *                             Counting is exact (unsigned long long).
 *
 * Edge indexing: edge between i<j has index e = i*(2n-i-1)/2 + (j-i-1),
 * so edge e corresponds to the e-th pair in lexicographic (i,j) order.
 */
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: brute n\n"); return 2; }
    int n = atoi(argv[1]);
    if (n < 2 || n > 9) { fprintf(stderr, "n out of supported range 2..9\n"); return 2; }
    int E = n * (n - 1) / 2;
    static unsigned long long counts[64] = {0};
    /* adjacency masks for every edge subset are built incrementally is complex;
       for n<=9 (E<=36) a per-subset rebuild is fast enough in C with -O2. */
    int ei[36], ej[36];
    int e = 0;
    for (int i = 0; i < n; i++)
        for (int j = i + 1; j < n; j++) { ei[e] = i; ej[e] = j; e++; }
    unsigned long long full = (1ULL << E);
    for (unsigned long long S = 0; S < full; S++) {
        int M = __builtin_popcountll(S);
        if (M < n - 1) continue;            /* can never be connected */
        unsigned long long adj[10] = {0,0,0,0,0,0,0,0,0,0};
        unsigned long long s = S;
        while (s) {
            int k = __builtin_ctzll(s);
            s &= s - 1;
            adj[ei[k]] |= 1ULL << ej[k];
            adj[ej[k]] |= 1ULL << ei[k];
        }
        /* BFS from vertex 0 */
        int dist[10], queue[10], qh = 0, qt = 0;
        unsigned long long seen = 1ULL;
        dist[0] = 0; queue[qt++] = 0;
        while (qh < qt) {
            int u = queue[qh++];
            unsigned long long m = adj[u] & ~seen;
            while (m) {
                int v = __builtin_ctzll(m);
                m &= m - 1;
                seen |= 1ULL << v;
                dist[v] = dist[u] + 1;
                queue[qt++] = v;
            }
        }
        if (seen != (1ULL << n) - 1) continue;   /* disconnected */
        int even = 0;
        for (int i = 0; i < n; i++) if (dist[i] % 2 == 0) even++;
        if (2 * even == n) counts[M]++;
    }
    for (int M = n - 1; M <= E; M++)
        printf("%llu%s", counts[M], M < E ? " " : "\n");
    return 0;
}
