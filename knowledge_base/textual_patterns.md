# Textual Patterns

Patterns discovered during development of the ledger editor.
Stub — fill in as development proceeds (Textual 8.2.5).

---

## Reactive Attributes

```python
from textual.reactive import reactive

class MyWidget(Widget):
    count = reactive(0)

    def watch_count(self, new_value: int) -> None:
        # Called automatically whenever count changes
        self.refresh()
```

- Use `reactive()` for state that should trigger re-renders.
- `watch_<name>` is called with the new value after each change.
- Avoid mutating reactive values inside `watch_*` to prevent recursion.

---

## Message Passing Between Widgets

```python
class MyMessage(Message):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.data = data

# In sender widget:
self.post_message(MyMessage("hello"))

# In receiver (parent or App):
def on_my_message(self, message: MyMessage) -> None:
    ...
```

Messages bubble up the DOM by default. Use `bubble=False` in the Message
class to prevent bubbling.

---

## CSS Variables

Textual's built-in CSS variables (from the default theme):

| Variable | Typical use |
|----------|-------------|
| `$primary` | Accent colour (borders, highlights) |
| `$secondary` | Secondary accent |
| `$background` | App background |
| `$surface` | Widget surface (panels, popups) |
| `$text` | Default text colour |
| `$text-muted` | Subdued text |
| `$success` | Positive feedback |
| `$warning` | Warning messages |
| `$error` | Error messages |

---

## Async Worker Pattern (Background I/O)

```python
from textual.worker import Worker, get_current_worker

class BalanceSidebar(Widget):
    async def refresh_balances(self) -> None:
        """Load balances without blocking the UI."""
        worker = self.run_worker(self._load_balances, exclusive=True)
        await worker.wait()

    async def _load_balances(self) -> dict:
        import PyLedger
        return PyLedger.load(self.journal_path).balance(tree=True)
```

Use `exclusive=True` to cancel any in-flight worker of the same type when a
new one starts (prevents stale updates on rapid Ctrl+S saves).

---

## Pilot Testing (for pytest-asyncio)

```python
async def test_app_starts(self):
    app = LedgerApp(Path("tests/fixtures/sample.journal"))
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.query_one(BalanceSidebar)
```

See Textual docs for `pilot.press()`, `pilot.click()`, `pilot.pause()`.

---

## Layer Overlay (Popups)

```python
class FilterPopup(Widget):
    DEFAULT_CSS = """
    FilterPopup {
        layer: overlay;
        ...
    }
    """
```

The parent App or Screen must declare `LAYERS = ("default", "overlay")` for
the layer to take effect.
