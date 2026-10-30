import sys

s = sys.argv[1]
d = open(s, 'rb').read()
p = 0
b = 0
n = 0

def g(k):
    global p, b, n
    while n < k:
        b |= d[p] << n
        p += 1
        n += 8
    v = b & ((1 << k) - 1)
    b >>= k
    n -= k
    return v

def tree(a):
    c = [0] * 16
    for x in a:
        c[x] += 1
    c[0] = 0
    q = [0] * 16
    v = 0
    for i in range(1, 16):
        v = (v + c[i - 1]) << 1
        q[i] = v
    t = {}
    for x, l in enumerate(a):
        if l:
            u = q[l]
            q[l] += 1
            r = 0
            for _ in range(l):
                r = (r << 1) | (u & 1)
                u >>= 1
            t[(l << 16) | r] = x
    return t

def sym(t):
    u = 0
    for l in range(1, 16):
        u |= g(1) << (l - 1)
        z = t.get((l << 16) | u)
        if z is not None:
            return z
    raise ValueError

L = [3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
E = [0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
D = [1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
F = [0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
o = bytearray()
last = 0
while not last:
    last = g(1)
    typ = g(2)
    if typ == 0:
        g(n & 7)
        m = g(16)
        g(16)
        for _ in range(m):
            o.append(g(8))
        continue
    if typ == 1:
        x = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
        y = [5] * 32
    else:
        h = g(5) + 257
        f = g(5) + 1
        k = g(4) + 4
        a = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]
        z = [0] * 19
        for i in range(k):
            z[a[i]] = g(3)
        z = tree(z)
        v = []
        while len(v) < h + f:
            x = sym(z)
            if x < 16:
                v.append(x)
            elif x == 16:
                v += [v[-1]] * (g(2) + 3)
            elif x == 17:
                v += [0] * (g(3) + 3)
            else:
                v += [0] * (g(7) + 11)
        x = v[:h]
        y = v[h:h + f]
    x = tree(x)
    y = tree(y)
    while True:
        q = sym(x)
        if q < 256:
            o.append(q)
        elif q == 256:
            break
        else:
            q -= 257
            m = L[q] + g(E[q])
            q = sym(y)
            k = D[q] + g(F[q])
            for _ in range(m):
                o.append(o[-k])
sys.stdout.buffer.write(o)
