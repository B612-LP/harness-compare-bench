import sys

class R:
    def __init__(self, d):
        self.d = d
        self.p = 0
        self.b = 0
        self.n = 0

    def bit(self):
        if self.n == 0:
            self.b = self.d[self.p]
            self.p += 1
            self.n = 8
        self.n -= 1
        return (self.b >> (7 - self.n)) & 1

    def bits(self, k):
        v = 0
        for i in range(k):
            v |= self.bit() << i
        return v

    def align(self):
        self.n = 0


def table(lens):
    mx = max(lens) if lens else 0
    cnt = [0] * (mx + 1)
    for x in lens:
        if x:
            cnt[x] += 1
    nxt = [0] * (mx + 1)
    code = 0
    for k in range(1, mx + 1):
        code = (code + cnt[k - 1]) << 1
        nxt[k] = code
    t = {}
    for sym, ln in enumerate(lens):
        if ln:
            t[(ln, nxt[ln])] = sym
            nxt[ln] += 1
    return t, mx


def dec(r, t, mx):
    c = 0
    for k in range(1, mx + 1):
        c = (c << 1) | r.bit()
        v = t.get((k, c))
        if v is not None:
            return v
    return -1


LB = [3,4,5,6,7,8,9,10,11,13,15,17,19,23,27,31,35,43,51,59,67,83,99,115,131,163,195,227,258]
LE = [0,0,0,0,0,0,0,0,1,1,1,1,2,2,2,2,3,3,3,3,4,4,4,4,5,5,5,5,0]
DB = [1,2,3,4,5,7,9,13,17,25,33,49,65,97,129,193,257,385,513,769,1025,1537,2049,3073,4097,6145,8193,12289,16385,24577]
DE = [0,0,0,0,1,1,2,2,3,3,4,4,5,5,6,6,7,7,8,8,9,9,10,10,11,11,12,12,13,13]
ORD = [16,17,18,0,8,7,9,6,10,5,11,4,12,3,13,2,14,1,15]


def inflate(d):
    r = R(d)
    out = bytearray()
    while True:
        final = r.bit()
        typ = r.bits(2)
        if typ == 0:
            r.align()
            ln = d[r.p] | (d[r.p + 1] << 8)
            r.p += 4
            out += d[r.p:r.p + ln]
            r.p += ln
        else:
            if typ == 1:
                ll = [8] * 144 + [9] * 112 + [7] * 24 + [8] * 8
                dl = [5] * 32
            elif typ == 2:
                hl = r.bits(5) + 257
                hd = r.bits(5) + 1
                hc = r.bits(4) + 4
                cl = [0] * 19
                for i in range(hc):
                    cl[ORD[i]] = r.bits(3)
                ct, cm = table(cl)
                lens = []
                while len(lens) < hl + hd:
                    s = dec(r, ct, cm)
                    if s < 16:
                        lens.append(s)
                    elif s == 16:
                        lens.extend([lens[-1]] * (3 + r.bits(2)))
                    elif s == 17:
                        lens.extend([0] * (3 + r.bits(3)))
                    else:
                        lens.extend([0] * (11 + r.bits(7)))
                ll = lens[:hl]
                dl = lens[hl:hl + hd]
            else:
                return bytes(out)
            lt, lm = table(ll)
            dt, dm = table(dl)
            while True:
                s = dec(r, lt, lm)
                if s < 256:
                    out.append(s)
                elif s == 256:
                    break
                else:
                    i = s - 257
                    ln = LB[i] + r.bits(LE[i])
                    j = dec(r, dt, dm)
                    ds = DB[j] + r.bits(DE[j])
                    for _ in range(ln):
                        out.append(out[-ds])
        if final:
            break
    return bytes(out)


f = sys.argv[1]
g = open(f, 'rb')
data = g.read()
g.close()
sys.stdout.buffer.write(inflate(data))
