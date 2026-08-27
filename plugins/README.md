# MyClaw plugins

Tambahkan modul Python di folder ini. Modul dapat menyediakan salah satu bentuk berikut:

```python
def get_tools():
    return [MyTool()]
```

Workflow bawaan dapat dijalankan dengan `/workflow system_report` atau `/workflow capture_screen`.

Plugin dimuat saat startup. Tool tetap melewati `safe_execute` dan policy approval yang sama.
