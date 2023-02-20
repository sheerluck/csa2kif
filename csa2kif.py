import sys
from re import sub
from math import ceil
from pathlib import Path
from multipledispatch import dispatch
from forbiddenfruit import curse


def prepare() -> tuple:
    # stripMargin from Scala
    curse(str, "_", lambda txt: sub("\n[ ]*\|", "\n", txt))

    info: dict = {"to": {}}
    s1 = "１２３４５６７８９"
    s2 = "一二三四五六七八九"
    for a, b in zip(s1, range(1, 10)):
        for m, n in zip(s2, range(1, 10)):
            x = f"{10*b + n}"
            fam = f"{a}{m}"
            info["to"][x] = fam

    info["piece"] = {
        "FU": "歩",     "KY": "香",     "KE": "桂",
        "GI": "銀",     "KI": "金",     "KA": "角",
        "HI": "飛",     "OU": "玉",
        "TO": "歩成",   "NY": "香成",   "NK": "桂成",
        "NG": "銀成",   "UM": "角成",   "RY": "飛成",
    }

    info["promo"] = {
        "TO": "と",     "NY": "成香",   "NK": "成桂",
        "NG": "成銀",   "UM": "馬",     "RY": "龍"}

    info["end"] = {
        "%TORYO":        "投了",
        "%TSUMI":        "詰み",
        "%CHUDAN":       "中断",
        "%SENNICHITE":   "千日手",
        "%TIME_UP":      "切れ負け",
        "%ILLEGAL_MOVE": "反則負け",
        "%JISHOGI":      "持将棋",
        "%KACHI":        "入力宣言"}

    game = {"moves": [],
            "times": {"+": 0, "-": 0},
            "promo": {},  # 33 -> "RY"
            "start": "?",
            "end":   "?",
            "n": 0}
    return game, info


def maybe_time(game: dict, line: str) -> None:
    start, end = "$START_TIME:", "$END_TIME:"
    if line.startswith(start):
        game["start"] = line.removeprefix(start)
    elif line.startswith(end):
        game["end"] = line.removeprefix(end)
    elif line.startswith("$SITE:"):
        game["url"] = line.removeprefix("$SITE:")
    elif line.startswith("$EVENT:ぴよ将棋"):
        game["url"] = "https://studiok-i.net/ps/"
    else:
        pass  # for now


def maybe_name(game: dict, line: str) -> None:
    if line.startswith("N+"):
        game["sente"] = line[2:]
    elif line.startswith("N-"):
        game["gote"] = line[2:]
    else:
        pass  # for now


def unclench(s: str) -> list[str]:
    # +1234FU,T5 -> [12, 34, FU, 5]
    return [s[1:3], s[3:5], s[5:7], s[9:]]


@dispatch(str, dict, str)
def from_sec(s: str, game: dict, line: str) -> int:
    time = game["times"][line[0]]
    if s:
        time += int(s)
    game["times"][line[0]] = time
    return time


@dispatch(int)
def from_sec(sec: int) -> tuple:
    h, M = divmod(ceil(sec), 60 * 60)
    m, s = divmod(M, 60)
    return h, m, s


@dispatch(str, int)
def from_sec(sec: str, time: int) -> str:
    if not sec:
        sec = "0"
    _, M, S = from_sec(int(sec))
    h, m, s = from_sec(time)
    return "{:>2}:{:02}/{:02}:{:02}:{:02}".format(M, S, h, m, s)


def maybe_replace(info: dict, game: dict, line: str) -> str:
    from_, to_, piece, sec = unclench(line)
    c = info["piece"][piece]
    p = game["promo"]
    if pr := p.get(from_):
        del p[from_]
        p[to_] = pr
        c = info["promo"][piece]
    else:  # first time
        p[to_] = piece
    return c


def maybe_old_promo_cleanup(game: dict, line: str) -> None:
    from_, to_, piece, sec = unclench(line)
    p = game["promo"]
    if to_ in p:
        del p[to_]


def move_and_time(info: dict, game: dict, line: str) -> None:
    if 1 == len(line):
        return

    game["n"] += 1
    from_, to_, piece, sec = unclench(line)
    time = from_sec(sec, game, line)
    a = game["n"]
    b = info["to"][to_]
    if b == game.get("prev"):
        b = "同　"
    c = info["piece"][piece]
    d = from_
    t = from_sec(sec, time)

    # promo stuff
    if "成" in c:
        c = maybe_replace(info, game, line)
    else:
        maybe_old_promo_cleanup(game, line)

    bcd = f"{b}{c}打" if "00" == from_ else f"{b}{c}({d})"
    if 8 == len(bcd) or "00" == from_:
        move = f"{a:>4}   {bcd:<10}    ({t})\n"
    else:
        move = f"{a:>4}   {bcd:<11}    ({t})\n"
    game["moves"].append(move)
    game["was"] = line[0]
    if "同" in b:
        pass
    else:
        game["prev"] = b


def game_over(info: dict, game: dict, line: str) -> None:
    game["n"] += 1
    a = game["n"]
    if "," in line:
        line = line.split(",")[0]
    bcd = info["end"][line]
    del game["times"][game["was"]]
    time = list(game["times"].values())[0]
    t = from_sec("0", time)
    move = f"{a:>4}   {bcd:<12}    ({t})\n"
    game["moves"].append(move)

    winner = "先手" if game["was"] == "+" else "後手"
    if "SEN" in line:
        result = "千日手"
    elif "TSUMI" in line:
        result = bcd
    else:
        result = f"{winner}の勝ち"
    move = f"まで{a-1}手で{result}\n\n"
    game["moves"].append(move)


def iterate_lines(fn: str, game: dict, info: dict) -> None:
    # main loop
    with open(fn, "r") as csa:
        for line in csa.read().splitlines():
            if not line:
                continue
            match line[0]:
                case "'" | "V" | "P":
                    pass
                case "N":
                    maybe_name(game, line)
                case "+" | "-":
                    move_and_time(info, game, line)
                case "$":
                    maybe_time(game, line)
                case "%":
                    game_over(info, game, line)
                case _:
                    print(line)


def write(fn: str, game: dict) -> None:

    with open(fn, "w") as kif:
        url = "https://syougi.qinoa.com/ja/game"
        if site := game.get("url"):
            url = site
        header = f"""
            |# ---- csa2kif.py ----
            |棋戦：Casual Blitz game
            |場所：{url}
            |開始日時：{game["start"]}
            |終了日時：{game["end"]}
            |持ち時間：5分秒読み10秒
            |手合割：平手
            |先手：{game["sente"]}
            |後手：{game["gote"]}
            |手数----指手---------消費時間--
            |"""._()
        kif.write(header[1:])
        for move in game["moves"]:
            kif.write(move)


def main() -> int:
    fn = sys.argv[1]  # *.csa

    game, info = prepare()
    iterate_lines(fn, game, info)

    fn = str(Path(fn).with_suffix(".x.kif"))
    write(fn, game)
    return 0


if __name__ == "__main__":
    exit(main())
