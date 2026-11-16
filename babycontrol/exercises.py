"""Auto-generated Math and English exercises (FEAT-002).

No hand-written question bank is needed: Math is generated from the grade,
English from a built-in vocabulary list by grade band.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

# (english, vietnamese) pairs per grade band.
VOCAB: dict[str, list[tuple[str, str]]] = {
    "g1-2": [
        ("cat", "con mèo"), ("dog", "con chó"), ("book", "quyển sách"),
        ("apple", "quả táo"), ("water", "nước"), ("red", "màu đỏ"),
        ("blue", "màu xanh dương"), ("mother", "mẹ"), ("father", "bố"),
        ("house", "ngôi nhà"), ("sun", "mặt trời"), ("fish", "con cá"),
        ("milk", "sữa"), ("bird", "con chim"), ("hand", "bàn tay"),
        ("eye", "con mắt"), ("tree", "cái cây"), ("ball", "quả bóng"),
    ],
    "g3-4": [
        ("breakfast", "bữa sáng"), ("teacher", "giáo viên"), ("window", "cửa sổ"),
        ("kitchen", "nhà bếp"), ("market", "chợ"), ("holiday", "kỳ nghỉ"),
        ("weather", "thời tiết"), ("library", "thư viện"), ("friend", "bạn bè"),
        ("rainbow", "cầu vồng"), ("farmer", "nông dân"), ("pencil", "bút chì"),
        ("bicycle", "xe đạp"), ("forest", "khu rừng"), ("island", "hòn đảo"),
        ("garden", "khu vườn"), ("tiger", "con hổ"), ("monkey", "con khỉ"),
    ],
    "g5-6": [
        ("environment", "môi trường"), ("beautiful", "xinh đẹp"),
        ("dangerous", "nguy hiểm"), ("exercise", "tập thể dục"),
        ("language", "ngôn ngữ"), ("journey", "chuyến đi"),
        ("different", "khác nhau"), ("important", "quan trọng"),
        ("vegetable", "rau củ"), ("hospital", "bệnh viện"),
        ("question", "câu hỏi"), ("music", "âm nhạc"),
        ("travel", "đi du lịch"), ("healthy", "khỏe mạnh"),
        ("popular", "phổ biến"), ("continue", "tiếp tục"),
    ],
    "g7+": [
        ("achievement", "thành tích"), ("opportunity", "cơ hội"),
        ("knowledge", "kiến thức"), ("responsible", "có trách nhiệm"),
        ("experience", "kinh nghiệm"), ("communicate", "giao tiếp"),
        ("temperature", "nhiệt độ"), ("necessary", "cần thiết"),
        ("government", "chính phủ"), ("pollution", "ô nhiễm"),
        ("education", "giáo dục"), ("celebrate", "kỷ niệm, ăn mừng"),
        ("attitude", "thái độ"), ("compare", "so sánh"),
        ("develop", "phát triển"), ("nervous", "lo lắng"),
    ],
}


def vocab_band(grade: int) -> str:
    if grade <= 2:
        return "g1-2"
    if grade <= 4:
        return "g3-4"
    if grade <= 6:
        return "g5-6"
    return "g7+"


@dataclass(frozen=True)
class Question:
    subject: str            # "math" | "english"
    prompt: str
    answer: str
    choices: tuple[str, ...] = ()   # empty = free-text answer

    def check(self, response: str) -> bool:
        response = response.strip()
        if self.subject == "math":
            try:
                return Decimal(response.replace(",", ".")) == Decimal(self.answer)
            except InvalidOperation:
                return False
        return response.casefold() == self.answer.casefold()


# --- Math ---------------------------------------------------------------

def _fmt(value: Decimal) -> str:
    text = format(value.normalize(), "f")
    return text


def math_question(grade: int, rng: random.Random) -> Question:
    grade = max(1, min(12, grade))
    if grade == 1:
        a, b = rng.randint(1, 10), rng.randint(1, 10)
        return _arith(a, "+", b) if rng.random() < 0.6 else _arith(max(a, b), "-", min(a, b))
    if grade == 2:
        a, b = rng.randint(10, 99), rng.randint(1, 50)
        return _arith(a, "+", b) if rng.random() < 0.5 else _arith(max(a, b), "-", min(a, b))
    if grade == 3:
        kind = rng.choice(["add", "sub", "mul"])
        if kind == "mul":
            return _arith(rng.randint(2, 10), "×", rng.randint(2, 10))
        a, b = rng.randint(100, 999), rng.randint(10, 500)
        return _arith(a, "+", b) if kind == "add" else _arith(max(a, b), "-", min(a, b))
    if grade == 4:
        kind = rng.choice(["mul", "div", "add"])
        if kind == "mul":
            return _arith(rng.randint(12, 99), "×", rng.randint(3, 9))
        if kind == "div":
            b = rng.randint(2, 9)
            return _arith(b * rng.randint(11, 99), "÷", b)
        return _arith(rng.randint(1000, 9999), "+", rng.randint(100, 5000))
    if grade == 5:
        kind = rng.choice(["dec_add", "dec_sub", "mul"])
        if kind == "mul":
            return _arith(rng.randint(12, 49), "×", rng.randint(11, 29))
        a = Decimal(rng.randint(10, 999)) / 10
        b = Decimal(rng.randint(10, 999)) / 10
        if kind == "dec_add":
            return Question("math", f"{_fmt(a)} + {_fmt(b)} = ?", _fmt(a + b))
        hi, lo = max(a, b), min(a, b)
        return Question("math", f"{_fmt(hi)} - {_fmt(lo)} = ?", _fmt(hi - lo))
    # grade 6+
    kind = rng.choice(["percent", "equation", "negative"])
    if kind == "percent":
        pct = rng.choice([10, 20, 25, 50, 75])
        base = rng.choice([40, 80, 120, 200, 400])
        return Question("math", f"{pct}% của {base} là bao nhiêu?", str(base * pct // 100))
    if kind == "equation":
        x, a, b = rng.randint(1, 15), rng.randint(2, 9), rng.randint(1, 20)
        return Question("math", f"Tìm x: {a}x + {b} = {a * x + b}", str(x))
    a, b = rng.randint(-20, 20), rng.randint(-20, 20)
    sign = "+" if b >= 0 else "-"
    return Question("math", f"{a} {sign} {abs(b)} = ?", str(a + b))


def _arith(a: int, op: str, b: int) -> Question:
    result = {"+": a + b, "-": a - b, "×": a * b, "÷": a // b if b else 0}[op]
    return Question("math", f"{a} {op} {b} = ?", str(result))


# --- English ------------------------------------------------------------

def english_question(grade: int, rng: random.Random) -> Question:
    pool = VOCAB[vocab_band(grade)]
    en, vi = rng.choice(pool)
    kind = rng.choice(["en2vi", "vi2en", "spell"])
    if kind == "spell" and len(en) < 3:
        kind = "en2vi"
    if kind == "spell":
        idx = rng.randrange(len(en))
        masked = en[:idx] + "_" + en[idx + 1:]
        return Question("english", f"Điền chữ cái còn thiếu: {masked}  ({vi})", en[idx])
    others = [p for p in pool if p[0] != en]
    wrong = rng.sample(others, 3)
    if kind == "en2vi":
        choices = [vi] + [w[1] for w in wrong]
        rng.shuffle(choices)
        return Question("english", f'"{en}" nghĩa là gì?', vi, tuple(choices))
    choices = [en] + [w[0] for w in wrong]
    rng.shuffle(choices)
    return Question("english", f'Từ tiếng Anh của "{vi}" là gì?', en, tuple(choices))


# --- Session ------------------------------------------------------------

class ExerciseSession:
    """Child must answer `required_correct` questions correctly to pass.

    Math and English alternate. A wrong answer is replaced by a fresh
    question so the answer cannot simply be retried.
    """

    def __init__(self, grade: int, required_correct: int,
                 rng: random.Random | None = None) -> None:
        self.grade = grade
        self.required_correct = required_correct
        self.correct = 0
        self.wrong = 0
        self._rng = rng or random.Random()
        self._turn = 0
        self.current: Question | None = None
        self._advance()

    def _advance(self) -> None:
        make = math_question if self._turn % 2 == 0 else english_question
        self._turn += 1
        self.current = make(self.grade, self._rng)

    @property
    def passed(self) -> bool:
        return self.correct >= self.required_correct

    def submit(self, response: str) -> bool:
        """Grade the current question; move on. Returns True if correct."""
        if self.passed or self.current is None:
            return False
        ok = self.current.check(response)
        if ok:
            self.correct += 1
        else:
            self.wrong += 1
        if self.passed:
            self.current = None
        else:
            self._advance()
        return ok
