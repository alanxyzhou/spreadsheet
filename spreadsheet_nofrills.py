import abc
from typing import Dict, Set, Tuple


class Expression(abc.ABC):
    def eval(self) -> int: ...


class Calculable(Expression, abc.ABC):
    def eval(self) -> int: ...


class Value(Calculable):
    def __init__(self, value: int):
        self.value = value

    def eval(self) -> int:
        return self.value


class CellRef(Calculable):
    def __init__(self, cell_ref: str):
        self.cell_ref = cell_ref

    def eval(self) -> int:
        return Spreadsheet.inst().get_cell(self.cell_ref)


class Addition(Expression):
    def __init__(self, lhs: Calculable, rhs: Calculable):
        self.lhs = lhs
        self.rhs = rhs

    def eval(self) -> int:
        return self.lhs.eval() + self.rhs.eval()


class Cell:
    def __init__(self, id: str):
        self.id: str = id
        self.expression: Expression = Value(0)
        self.value: int = 0
        self.subscribers: Set[Cell] = set()

    def set_value(self, expression: Expression):
        self.expression = expression
        self.value = self.expression.eval()
        for s in self.subscribers:
            s.notify()

    def get_value(self) -> int:
        return self.value

    def add_subscriber(self, other):
        self.subscribers.add(other)

    def notify(self):
        self.set_value(self.expression)
        for s in self.subscribers:
            s.notify()


class CellDict(Dict):
    def __init__(self, factory):
        self.factory = factory

    def __missing__(self, key):
        self[key] = self.factory(key)
        return self[key]


class Spreadsheet:
    _inst = None

    @staticmethod
    def inst():
        if Spreadsheet._inst is None:
            Spreadsheet._inst = Spreadsheet()
        return Spreadsheet._inst

    def __init__(self):
        self.cells: Dict[str, Cell] = CellDict(lambda id: Cell(id))

    def get_cell(self, id) -> int:
        cell = self.inst().cells[id]
        return cell.get_value()

    def set_cell(self, id: str, raw_expr: str) -> None:
        target_cell = self.inst().cells[id]

        expr, cell_refs = self.parse_expr(raw_expr)

        target_cell.set_value(expr)

        for subscribee in cell_refs:
            dependency_cell = self.inst().cells[str(subscribee)]
            self.subscribe_cell(target_cell, dependency_cell)

    def parse_expr(self, raw_expr: str) -> Tuple[Expression, Set[Cell]]:
        tokens = raw_expr.split()

        is_mid_expression = False
        prev_expression = None
        cell_refs = set()

        for tok in tokens:
            if is_mid_expression:
                calculable = self.parse_alphanumeric(tok)
                if isinstance(calculable, CellRef):
                    cell_refs.add(calculable)
                prev_expression = Addition(prev_expression, calculable)
                is_mid_expression = False
            else:
                if tok[0] == "+":
                    is_mid_expression = True
                else:
                    calculable = self.parse_alphanumeric(tok)
                    if isinstance(calculable, CellRef):
                        cell_refs.add(calculable)
                    prev_expression = calculable

        return prev_expression, cell_refs

    def parse_alphanumeric(self, tok: str) -> Calculable:
        if tok[0].isnumeric():
            return Value(int(tok))
        else:  # tok[0].isalpha()
            return CellRef(tok)

    def subscribe_cell(self, cell: Cell, dependent: Cell):
        dependent.add_subscriber(cell)


## tests
sheet = Spreadsheet.inst()

sheet.set_cell("A1", "3")
assert sheet.get_cell("A1") == 3

sheet.set_cell("B1", "A1")
assert sheet.get_cell("B1") == 3

sheet.set_cell("C1", "A1 + B1")
assert sheet.get_cell("C1") == 6

sheet.set_cell("A1", "2")
assert sheet.get_cell("A1") == 2
assert sheet.get_cell("B1") == 2
assert sheet.get_cell("C1") == 4

sheet.set_cell("D1", "8 + B1")
assert sheet.get_cell("D1") == 10

sheet.set_cell("E1", "B1 + 7")
assert sheet.get_cell("E1") == 9
