#!/usr/bin/env python3
"""corpus-squeeze 语料生成器 v0.1（2026-10-22）

固定种子确定性生成 ~200KB 中英混合语料，落盘为 inputs/corpus.txt 后冻结；
本脚本只用于证明复现方式（同种子重跑必须字节一致）。

构成（见 spec.md「阈值校准记录」）：
  1 头部横幅 + 2 JSON 行段（结构化）+ 3 管道表格段（结构化）
  4 伪 Python 代码段（高冗余）+ 5 中英自然段（主体）
  6 高熵随机段（base64(随机字节)，防「全是冗余随便压」）

确定性说明：只使用 random.Random(seed).randrange()——官方文档保证
randrange 序列跨 Python 版本不变；choice/shuffle 等包装一律不用。
"""
import base64
import random
import sys
from pathlib import Path

SEED = 20261022
TARGETS = {  # 各段目标字节数（UTF-8）
    "json": 33 * 1024,
    "table": 13 * 1024,
    "code": 25 * 1024,
    "prose": 100 * 1024,
    "random": 27 * 1024,
}


def pick(rng, seq):
    return seq[rng.randrange(len(seq))]


def sample(rng, seq, k):
    """无放回取 k 个（顺序随机），等价实现只用 randrange。"""
    pool = list(seq)
    out = []
    for _ in range(k):
        out.append(pool.pop(rng.randrange(len(pool))))
    return out


# ---------------------------------------------------------------- 词库
ZH_SUBJ = ["三号馆", "储物柜区", "自助打印机", "研讨间走廊", "东门闸机", "器材室",
           "看台下层", "空调机房", "消防通道", "前台服务台", "淋浴间", "器材借还处",
           "二楼连廊", "地下车库入口", "羽毛球场地", "乒乓球区", "健身房", "体测室",
           "医务室", "仓库东侧", "贵宾通道", "媒体工作间", "LED 大屏", "广播室"]
ZH_OBJ = ["巡检记录", "能耗台账", "预约流水", "报修工单", "清洁排班", "门禁日志",
          "器材清单", "耗材库存", "维修档案", "值班表", "开馆检查单", "闭馆核对单",
          "活动排期", "场地预约", "设备点检表", "安全巡查表", "物资领用单", "钥匙借还登记",
          "会议纪要", "公告栏内容", "通风计划", "照明策略", "停车数据", "客流统计"]
ZH_VERB = ["核对", "汇总", "复核", "归档", "抽查", "更新", "盘点", "整理", "补录", "比对",
           "追踪", "确认", "同步", "校验", "备份", "登记", "排查", "评估", "复核", "下发"]
ZH_ADJ = ["顺利", "正常", "略有延迟", "按计划", "提前完成", "仍在进行", "出现异常",
          "暂缓执行", "加急处理", "已完成", "待复核", "持续观察"]
ZH_CONN = ["随后", "与此同时", "另一方面", "此外", "随后不久", "在确认无误后",
           "经过交叉核对", "根据最新台账", "按照排班安排", "综合考虑之后"]
ZH_TAIL = ["没有发现新的问题。", "剩余事项转交晚班处理。", "相关记录已同步到台账。",
           "需要在天黑前完成复核。", "负责人已在群里确认。", "暂不需要额外的人手。",
           "异常项已挂牌并上报。", "第二天会安排一次复查。", "耗材缺口约为一成。",
           "整体进度符合预期。"]

EN_SUBJ = ["the front desk", "hall three", "the locker area", "the print station",
           "the east gate", "the equipment room", "the gym floor", "the lower stands",
           "the HVAC room", "the service counter", "the media booth", "the storeroom",
           "the corridor sensors", "the booking system", "the night shift",
           "the cleaning crew", "the maintenance team", "the info screen"]
EN_OBJ = ["the inspection log", "the energy ledger", "the booking records",
          "the repair tickets", "the duty roster", "the access logs",
          "the inventory list", "the maintenance archive", "the opening checklist",
          "the closing checklist", "the event schedule", "the visitor statistics",
          "the supply inventory", "the key registry", "the ventilation plan"]
EN_VERB = ["reviewed", "summarized", "double-checked", "archived", "sampled",
           "updated", "reconciled", "sorted", "cross-checked", "verified",
           "backed up", "re-registered", "evaluated", "published", "audited"]
EN_ADJ = ["smooth", "normal", "slightly delayed", "on schedule", "ahead of plan",
          "still in progress", "abnormal", "postponed", "expedited", "completed",
          "pending review", "under observation"]
EN_TAIL = ["no new issues were found.", "the rest was handed to the evening shift.",
           "the records were synced to the ledger.", "a second review is scheduled.",
           "the owner confirmed it in the group chat.", "no extra staffing is needed.",
           "the abnormal item was flagged and reported.", "overall progress is on track."]

NOUN_A = ["alpha", "bravo", "delta", "kappa", "orbit", "quartz", "signal", "vector",
          "cobalt", "meadow", "harbor", "lantern"]
NOUN_B = ["node", "window", "buffer", "stream", "ledger", "segment", "channel", "packet",
          "cursor", "token", "region", "sample"]
PLACES = ["hall1", "hall2", "hall3", "gym", "pool", "lobby", "yard", "roof"]
TAGS = ["indoor", "outdoor", "vip", "shared", "reserved", "tall", "wide", "mobile",
        "fixed", "quiet", "noisy", "new", "legacy", "audit", "night"]
STATUS = ["active", "idle", "repair", "retired", "testing"]
REGIONS = ["north", "south", "east", "west", "center"]


def section_json(rng, target):
    out = ["# SECTION-A JSON 行流水（每行一个对象）", ""]
    n = 1000 + rng.randrange(9)
    used = 0
    i = 0
    while used < target:
        i += 1
        rec = {
            "id": n + i,
            "sku": "SKU-%04x" % rng.randrange(0x10000),
            "name_zh": pick(rng, ZH_SUBJ) + "-" + pick(rng, ["东", "南", "西", "北", "中"]) + str(1 + rng.randrange(24)) + "号",
            "name_en": pick(rng, NOUN_A) + "-" + pick(rng, PLACES) + str(1 + rng.randrange(48)),
            "tags": sample(rng, TAGS, 1 + rng.randrange(4)),
            "qty": rng.randrange(0, 240),
            "price": "%d.%02d" % (rng.randrange(4000) / 100, rng.randrange(100)),
            "region": pick(rng, REGIONS),
            "status": pick(rng, STATUS),
        }
        line = json_line(rec)
        out.append(line)
        used += len(line.encode("utf-8")) + 1
    return out


def json_line(rec):
    import json
    return json.dumps(rec, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def section_table(rng, target):
    out = ["# SECTION-B 巡检表格（管道分隔，列名固定）", "",
           "| 序号 | 区域 | 区域代码 | 读数 | 日期 | 状态 | 备注 |",
           "|---:|---|---|---:|---|---|---|"]
    used = 0
    i = 0
    while used < target:
        i += 1
        row = "| T-%04d | %s | %s | %d | 2026-%02d-%02d | %s | %s |" % (
            i, pick(rng, ZH_SUBJ), pick(rng, PLACES).upper() + "-" + str(1 + rng.randrange(9)),
            rng.randrange(0, 999), 1 + rng.randrange(12), 1 + rng.randrange(28),
            pick(rng, STATUS), pick(rng, ZH_ADJ) + "；" + pick(rng, ZH_TAIL))
        out.append(row)
        used += len(row.encode("utf-8")) + 1
    return out


def section_code(rng, target):
    out = ["# SECTION-C 例行脚本骨架（同构函数群，冗余度高）", "", "import sys", ""]
    used = 0
    i = 0
    while used < target:
        i += 1
        name = "routine_%s_%02d" % (pick(rng, NOUN_A), i)
        body = []
        body.append("def %s(%s_id, %s):" % (name, pick(rng, NOUN_B), pick(rng, NOUN_B)))
        body.append('    """同步 %s 的 %s，返回处理结果。"""' % (pick(rng, ZH_OBJ), pick(rng, ZH_OBJ)))
        body.append("    payload = collect(%s_id, limit=%d)" % (pick(rng, NOUN_B), 8 + rng.randrange(120)))
        body.append("    if payload is None:")
        body.append('        log.warn("missing payload: %s" % ' + pick(rng, NOUN_B) + "_id)")
        body.append("        return False")
        body.append("    result = transform(payload, window=%d)" % (1 + rng.randrange(64)))
        body.append('    metrics.record("%s", len(result))' % name)
        body.append("    return result")
        body.append("")
        block = "\n".join(body) + "\n"
        out.append(block)
        used += len(block.encode("utf-8"))
    return out


def section_prose(rng, target):
    out = ["# SECTION-D 运营日志（中英自然段）", ""]
    used = 0
    day = 0
    while used < target:
        day += 1
        zh = ("%s，%s对%s进行了%s，情况%s。%s，%s还完成了备用%s的抽查，%s%s。" % (
            pick(rng, ["早晨", "上午", "中午", "下午", "闭馆前", "晚间"]),
            pick(rng, ZH_SUBJ), pick(rng, ZH_OBJ), pick(rng, ZH_VERB), pick(rng, ZH_ADJ),
            pick(rng, ZH_CONN), pick(rng, ["值班员", "领班", "技术组", "志愿者"]),
            pick(rng, ZH_OBJ), pick(rng, ZH_CONN), pick(rng, ZH_TAIL)))
        en = ("Today %s %s %s; the result was %s, and %s %s %s. %s." % (
            pick(rng, EN_SUBJ), pick(rng, EN_VERB), pick(rng, EN_OBJ),
            pick(rng, EN_ADJ), pick(rng, EN_SUBJ), pick(rng, EN_VERB), pick(rng, EN_OBJ),
            pick(rng, EN_TAIL).capitalize()))
        para_zh = "Day %03d（中文）：%s%s" % (day, zh, pick(rng, ZH_TAIL))
        para_en = "Day %03d (EN): %s In addition, %s %s %s, %s." % (
            day, en.capitalize(), pick(rng, EN_SUBJ), pick(rng, EN_VERB), pick(rng, EN_OBJ),
            pick(rng, EN_TAIL))
        block = para_zh + "\n\n" + para_en + "\n\n"
        out.append(block)
        used += len(block.encode("utf-8"))
    return out


def section_random(rng, target):
    out = ["# SECTION-E 高熵随机流（base64，请勿手改；用于防止全冗余语料）", ""]
    used = len(out[0].encode("utf-8")) + len(out[1].encode("utf-8")) + 2
    while used < target:
        raw = bytes(rng.randrange(256) for _ in range(48))
        line = base64.b64encode(raw).decode("ascii")
        out.append(line)
        used += len(line) + 1
    return out


def build() -> bytes:
    rng = random.Random(SEED)
    parts = ["# corpus-squeeze 语料 v0.1（种子 %d，生成器 environment/tools/gen_corpus.py）" % SEED, ""]
    parts += section_json(rng, TARGETS["json"])
    parts += ["", ]
    parts += section_table(rng, TARGETS["table"])
    parts += [""]
    parts += section_code(rng, TARGETS["code"])
    parts += [""]
    parts += section_prose(rng, TARGETS["prose"])
    parts += [""]
    parts += section_random(rng, TARGETS["random"])
    parts += ["# END OF CORPUS"]
    text = "\n".join(parts).rstrip("\n") + "\n"
    return text.encode("utf-8")


def main(argv):
    if len(argv) != 2:
        print("usage: python3 gen_corpus.py <output.txt>", file=sys.stderr)
        return 2
    data = build()
    Path(argv[1]).write_bytes(data)
    print("wrote %s: %d bytes" % (argv[1], len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
