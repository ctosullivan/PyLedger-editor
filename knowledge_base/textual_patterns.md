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
        import ledgerkit
        return ledgerkit.load(self.journal_path).balance(tree=True)
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

## Symmetric Scroll-Into-View Margin

```python
def scroll_cursor_visible(self, center: bool = False, animate: bool = False):
    ...
    return self.scroll_to_region(
        Region(x, y, width=3, height=1),
        spacing=Spacing(top=4, right=self.gutter_width, bottom=4),
        animate=animate,
        force=True,
        center=center,
    )
```

`TextArea._watch_selection()` (Textual 8.2.5) calls `scroll_cursor_visible()`
on every `move_cursor()`, and dispatches polymorphically — a subclass
override runs even though the call originates in the base class. Because of
that, **whatever `Spacing` this override uses applies to every cursor-moving
action in both directions**, not just the one you were thinking about when
you wrote it. A `bottom=`-only margin (added to keep downward navigation
from scrolling flush to the last row) silently leaves upward navigation with
no margin at all — there's no way to special-case one direction without
special-casing every caller of `move_cursor()`. Set `top=` and `bottom=` to
matching values unless you have a specific reason for asymmetry, and note
that reason here if you do.

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
