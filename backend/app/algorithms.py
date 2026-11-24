"""Deterministic rectangular Hungarian matching and a shared-matrix greedy baseline."""
import random
from time import perf_counter

def maximum_weight(matrix):
    n = len(matrix)
    if not n:
        return []
    width = len(matrix[0])
    assert all(len(row) == width for row in matrix)
    # One zero-valued dummy per request; prohibited edges can never beat a dummy.
    cost = [[-v if v is not None else 1e12 for v in row] + [0.0] * n for row in matrix]
    m = width + n
    u, v, p, way = [0.0] * (n+1), [0.0] * (m+1), [0] * (m+1), [0] * (m+1)
    for i in range(1, n+1):
        p[0] = i
        j0 = 0
        minimum, used = [float('inf')] * (m+1), [False] * (m+1)
        while True:
            used[j0] = True
            i0, delta, j1 = p[j0], float('inf'), 0
            for j in range(1, m+1):
                if not used[j]:
                    cur = cost[i0-1][j-1] - u[i0] - v[j]
                    if cur < minimum[j]:
                        minimum[j], way[j] = cur, j0
                    if minimum[j] < delta:
                        delta, j1 = minimum[j], j
            for j in range(m+1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while j0:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
    return sorted((p[j]-1, j-1) for j in range(1, width+1)
                  if p[j] and matrix[p[j]-1][j-1] is not None and matrix[p[j]-1][j-1] > 0)

def greedy(matrix):
    edges = sorted((-value, i, j) for i, row in enumerate(matrix)
                   for j, value in enumerate(row) if value is not None and value > 0)
    rows, cols, chosen = set(), set(), []
    for _, i, j in edges:
        if i not in rows and j not in cols:
            rows.add(i)
            cols.add(j)
            chosen.append((i, j))
    return sorted(chosen)

def summarize(matrix, pairs, scores, urgencies, elapsed):
    urgent = sum(x == 'Urgent' for x in urgencies)
    return {
        'assignment_count': len(pairs),
        'total_utility': round(sum(matrix[i][j] for i,j in pairs), 4),
        'average_suitability': round(sum(scores[i][j] for i,j in pairs)/len(pairs), 4) if pairs else 0,
        'urgent_assignment_rate': sum(urgencies[i] == 'Urgent' for i,j in pairs)/urgent if urgent else None,
        'unassigned_requests': len(matrix)-len(pairs),
        'invalid_assignments': sum(matrix[i][j] is None for i,j in pairs),
        'runtime_ms': elapsed * 1000,
    }

def benchmark(seed=15015, scenarios=50):
    rng, results = random.Random(seed), []
    for scenario in range(scenarios):
        n, m = rng.randint(2, 22), rng.randint(1, 25)
        urgency = [rng.choice(['Urgent','Normal','Flexible']) for _ in range(n)]
        scores = [[round(rng.uniform(35,100), 4) if rng.random() > .35 else None for _ in range(m)] for _ in range(n)]
        waits = [rng.uniform(0,10) for _ in range(n)]
        matrix = [[s * {'Urgent':1.25,'Normal':1,'Flexible':.85}[urgency[i]] + waits[i]
                   if s is not None else None for s in row] for i,row in enumerate(scores)]
        entry = {'scenario': scenario}
        for name, algorithm in [('optimized',maximum_weight),('greedy',greedy)]:
            start = perf_counter()
            pairs = algorithm(matrix)
            entry[name] = summarize(matrix, pairs, scores, urgency, perf_counter()-start)
        results.append(entry)
    return {'seed':seed, 'scenario_count':scenarios, 'scenarios':results,
            'optimized_wins':sum(r['optimized']['total_utility'] > r['greedy']['total_utility'] + .0001 for r in results),
            'equal':sum(abs(r['optimized']['total_utility']-r['greedy']['total_utility']) <= .0001 for r in results),
            'illustration': {'matrix':[[9,8],[8,1]], 'optimized':maximum_weight([[9,8],[8,1]]),
                             'greedy':greedy([[9,8],[8,1]]),
                             'optimized_utility':sum([[9,8],[8,1]][i][j] for i,j in maximum_weight([[9,8],[8,1]])),
                             'greedy_utility':sum([[9,8],[8,1]][i][j] for i,j in greedy([[9,8],[8,1]]))}}
