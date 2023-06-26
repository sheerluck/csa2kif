import sys
import json
from re import sub
from math import ceil
from time import strptime
from pathlib import Path
from multipledispatch import dispatch
from forbiddenfruit import curse


def prepare() -> tuple:
    # stripMargin from Scala
    curse(str, "_", lambda txt: sub("\n[ ]*\|", "\n", txt))

    info: dict = {"to": {}}
    s1 = "abcdefghijklmn"
    s2 = "一二三四五六七八九十MNXY"
    m1 = "lkjihgfedcba"
    m2 = "cba987654321"
    for a, b, q in zip(s1, range(1, 13), m1):
        for m, n, w in zip(s2, range(1, 13), m2):
            if n > 10:
                m = f"十{s2[-1+n%10]}"
            x = f"{a}{n}"
            fam = f"{b}{m}"
            w = {"c": 12, "b": 11, "a": 10}.get(w, w)
            madx = f"{q}{w}"
            info["to"][madx] = fam

    info["piece"] = {
        "P":  "歩兵",  "GB": "仲人",  "SM": "横行",
        "VM": "竪行",  "R":  "飛車",  "DH": "龍馬",
        "DK": "龍王",  "Ln": "獅子",  "Q":  "奔王", "FK":"奔王",
        "RC": "反車",  "B":  "角行",  "BT": "盲虎",
        "Kr": "麒麟",  "Ph": "鳳凰",  "L":  "香車",
        "FL": "猛豹",  "C":  "銅将",  "S":  "銀将",
        "G":  "金将",  "K":  "玉将",  "DE": "醉象",
        # remember 成 for some reason
        "HF+": "龍馬成",  "+B": "角行成",  "SE+": "龍王成",
    }

    info["promo"] = {
        # todo if actually needed
        "HF+": "角鷹",  "+B": "龍馬",   "SE+": "飛鷲",
        "xx": "成銀",   "xx": "馬",     "xx": "龍"}

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
            "time": "00:05+10",
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
    elif line.startswith("$TIME_LIMIT:"):
        game["time"] = line.removeprefix("$TIME_LIMIT:")
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
    # "P e4-e5" -> [P, e4, -, e5]
    ch = s.split(" ")
    result, ch = [ch[0]], ch[1]
    if '=' in ch:
        a, b = ch.split('=')
        if 'x' in a:
            result.extend(a.split('x'))
        elif '-' in a:
            result.extend(a.split('-'))
        result.append(b)
    elif '-' in ch:
        result.extend(ch.split('-'))
    elif 'x' in ch:
        result.extend(ch.split('x'))
    return result


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


def maybe_replace(info: dict, game: dict, line: tuple) -> str:
    from_, to_, piece = line
    c = info["piece"][piece]
    p = game["promo"]
    if pr := p.get(from_):
        del p[from_]
        p[to_] = pr
        c = info["promo"][piece]
    else:  # first time
        p[to_] = piece
    return c


def maybe_old_promo_cleanup(game: dict, to_: str) -> None:
    p = game["promo"]
    if to_ in p:
        del p[to_]


def move_and_time(info: dict, game: dict, line: str) -> None:
    Lnto2 = -1
    game["n"] += 1
    ah = unclench(line)
    #time = from_sec(sec, game, line)
    if ah[0] == "Ln":
        #special
        if (how := line.count('-')) == 1:
            piece, from_, to_ = ah
        else:
            piece, from_, to_, Lnto2 = ah
    else:
        if len(ah) == 4:  #promo
            old, from_, to_, piece = ah  # "DH i7xf4=HF+",
        else:
            piece, from_, to_ = ah

    a = game["n"]
    b = info["to"][to_]
    if b == game.get("prev"):
        b = "仝"
    c = info["piece"][piece]
    d = info["to"][from_]
    #t = from_sec(sec, time)

    # promo stuff
    if "成" in c:
        line = from_, to_, piece
        c = maybe_replace(info, game, line)
    else:
        maybe_old_promo_cleanup(game, to_)

    bcd = f"{b}{c} （←{d}）"

    move = f"{a:>4}手目   {bcd:<9}\n"
    if Lnto2 != -1:
        move = f"{a:>4}手目一歩目 {bcd:<9}\n"
        game["moves"].append(move)
        from_, to_ = to_, Lnto2
        b = info["to"][to_]
        d = info["to"][from_]
        bcd = f"{b}{c} （←{d}）"
        move = f"{a:>4}手目二歩目 {bcd:<9}\n"

    game["moves"].append(move)
    game["was"] = '+' if a%2 else '-'
    if "仝" in b:
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
    with open(fn, "r") as jj:
        data = json.load(jj)
        for line in data["actions"]:
            move_and_time(info, game, line)


def parse_time(s: str) -> tuple:
    # "00:05+10" -> 5, 10
    a, b = s.split("+")
    t, b = strptime(a, "%H:%M"), strptime(b, "%S")
    return t.tm_hour * 60 + t.tm_min, b.tm_sec


def write(fn: str, game: dict) -> None:

    with open(fn, "w") as kif:
        hm, byoyomi = parse_time(game["time"])
        url = "https://syougi.qinoa.com/ja/game"
        if site := game.get("url"):
            url = site
        header = f"""
            |# ---- json2kif.py ----
            |棋戦：Rated Chushogi game
            |場所：{url}
            |開始日時：{game["start"]}
            |終了日時：{game["end"]}
            |持ち時間：{hm}分秒読み{byoyomi}秒
            |手合割：平手
            |先手：{game.get("sente", 'A')}
            |後手：{game.get("gote",  'B')}
            |手数----指手---------消費時間--
            |"""._()
        kif.write(header[1:])
        for move in game["moves"]:
            kif.write(move)


def main() -> int:
    fn = sys.argv[1]  # *.json  *.mgs

    game, info = prepare()
    iterate_lines(fn, game, info)

    fn = str(Path(fn).with_suffix(".x.kif"))
    write(fn, game)
    return 0


if __name__ == "__main__":
    exit(main())
