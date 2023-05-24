from .scripter import Scripter


class FishScripter(Scripter):
    """A specialized Scripter for fish. Pass a instance of this class to `source` to source fish scripts."""

    def dereference(self, variable: str) -> str:
        return f"{{${variable}}}"
