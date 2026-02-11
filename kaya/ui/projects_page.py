from __future__ import annotations
from PySide6 import QtWidgets, QtCore, QtGui
from pathlib import Path
import json, shutil, datetime, os, re, uuid

# ----------------- Genel sabitler -----------------
META_DIR  = ".kaya"
META_FILE = "project.json"

# --- Simple FlowLayout (Qt örneklerinden uyarlanmış) ---
class FlowLayout(QtWidgets.QLayout):
    def __init__(self, parent=None, margin=0, hspacing=22, vspacing=16):
        super().__init__(parent)
        self._items = []
        self.setContentsMargins(margin, margin, margin, margin)
        self._h = hspacing
        self._v = vspacing
    def addItem(self, item): self._items.append(item)
    def count(self): return len(self._items)
    def itemAt(self, i): return self._items[i] if 0 <= i < len(self._items) else None
    def takeAt(self, i): return self._items.pop(i) if 0 <= i < len(self._items) else None
    def expandingDirections(self): return QtCore.Qt.Orientations(QtCore.Qt.Orientation(0))
    def hasHeightForWidth(self): return True
    def heightForWidth(self, w): return self._do_layout(QtCore.QRect(0,0,w,0), True)
    def setGeometry(self, rect): super().setGeometry(rect); self._do_layout(rect, False)
    def sizeHint(self): return self.minimumSize()
    def minimumSize(self):
        s = QtCore.QSize()
        for it in self._items:
            s = s.expandedTo(it.minimumSize())
        m = self.contentsMargins()
        s += QtCore.QSize(2*m.left(), 2*m.top())
        return s
    def _do_layout(self, rect, test_only):
        x = rect.x() + self.contentsMargins().left()
        y = rect.y() + self.contentsMargins().top()
        line_height = 0
        right = rect.right() - self.contentsMargins().right()
        for it in self._items:
            w = it.sizeHint().width()
            h = it.sizeHint().height()
            if x + w > right and line_height > 0:
                x = rect.x() + self.contentsMargins().left()
                y += line_height + self._v
                line_height = 0
            if not test_only:
                it.setGeometry(QtCore.QRect(QtCore.QPoint(x, y), it.sizeHint()))
            x += w + self._h
            line_height = max(line_height, h)
        return y + line_height - rect.y()

# --- Proje gezgininde .kaya ve dot-file'ları gizle ---
class ProjectProxyFilter(QtCore.QSortFilterProxyModel):
    def __init__(self, proj_dir: Path, parent=None):
        super().__init__(parent)
        self.proj_dir = proj_dir
    def filterAcceptsRow(self, source_row, source_parent):
        idx = self.sourceModel().index(source_row, 0, source_parent)
        if not idx.isValid():
            return True
        p = Path(self.sourceModel().filePath(idx))
        try:
            rel = p.relative_to(self.proj_dir)
        except Exception:
            return False
        parts = rel.parts
        # .kaya klasörü ve noktayla başlayan her şey gizli
        if any(part.startswith(".") for part in parts):
            return False
        return True

# ----------------- küçük yardımcılar -----------------
def now_iso(): return datetime.datetime.now().isoformat(timespec="seconds")
def read_json(p: Path, default: dict):
    try: return json.loads(p.read_text(encoding="utf-8"))
    except Exception: return dict(default)
def write_json(p: Path, data: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
def ensure_unique_path(p: Path) -> Path:
    if not p.exists(): return p
    stem, suf = p.stem, p.suffix
    parent = p.parent; i = 1
    while True:
        cand = parent / f"{stem} ({i}){suf}"
        if not cand.exists(): return cand
        i += 1
def is_image_file(path: Path) -> bool:
    return path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}

def is_textish_file(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".json", ".py", ".js", ".ts", ".html", ".css", ".csv", ".yaml", ".yml"}

def safe_child_path(root: Path, candidate: Path) -> Path | None:
    try:
        candidate.resolve().relative_to(root.resolve())
        return candidate
    except Exception:
        return None

def slugify(name: str) -> str:
    # Windows yasaklı karakterleri temizle, boşlukları tire yap
    name = re.sub(r'[\\/*?:"<>|]+', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.replace(' ', '-')
    tr = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    name = name.translate(tr)
    name = re.sub(r'[^A-Za-z0-9\-_]+', '', name)
    return name or "project"

def shortid(n: int = 6) -> str:
    return uuid.uuid4().hex[:n].upper()

DEFAULT_META = {
    "name": "", "type": "standard", "status": "active",
    "tags": [], "created_at": "", "updated_at": "",
    "color": "", "progress": 0, "pinned": False
}
TYPE_COLORS = {
    "standard":   "#00C2C7",
    "engineering":"#D97A00",
    "edu":        "#5BA3FF",
    "research":   "#2AB39A",
    "custom":     "#B38BFA",
}
TYPE_ORDER = ["standard","engineering","edu","research","custom"]

# ----------------- Görsel Görüntüleyici -----------------
class ImageViewer(QtWidgets.QWidget):
    """Kaydırılabilir, zoom'lu basit görüntüleyici + toolbar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pix = QtGui.QPixmap()
        self._scale = 1.0
        self._fit = True

        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0); v.setSpacing(4)
        # Toolbar
        tb = QtWidgets.QToolBar()
        self.act_zoom_in  = tb.addAction("Zoom In")
        self.act_zoom_out = tb.addAction("Zoom Out")
        self.act_fit      = tb.addAction("Fit")
        self.act_actual   = tb.addAction("Actual")
        tb.addSeparator()
        self.act_full     = tb.addAction("Fullscreen")
        v.addWidget(tb)

        # Scrollable label
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.label.setBackgroundRole(QtGui.QPalette.Base)
        self.label.setSizePolicy(QtWidgets.QSizePolicy.Ignored, QtWidgets.QSizePolicy.Ignored)
        self.scroll.setWidget(self.label)
        v.addWidget(self.scroll, 1)

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self, self.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+="), self, self.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self, self.zoom_out)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, self.fit)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+1"), self, self.actual)
        QtGui.QShortcut(QtGui.QKeySequence("F11"), self, self.fullscreen)

        self.act_zoom_in.triggered.connect(self.zoom_in)
        self.act_zoom_out.triggered.connect(self.zoom_out)
        self.act_fit.triggered.connect(self.fit)
        self.act_actual.triggered.connect(self.actual)
        self.act_full.triggered.connect(self.fullscreen)

    def load(self, path: Path):
        pm = QtGui.QPixmap(str(path))
        if pm.isNull():
            QtWidgets.QMessageBox.warning(self, "Image", f"Görüntü yüklenemedi:\n{path}")
            return
        self._pix = pm
        self._scale = 1.0
        self._fit = True
        self._apply()

    def _apply(self):
        if self._pix.isNull():
            self.label.clear(); return
        if self._fit:
            avail = self.scroll.viewport().size()
            if not avail.isEmpty():
                scaled = self._pix.scaled(avail, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.label.setPixmap(scaled)
                return
        # actual/zoom
        w = int(self._pix.width() * self._scale)
        h = int(self._pix.height() * self._scale)
        scaled = self._pix.scaled(w, h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        if self._fit:
            QtCore.QTimer.singleShot(0, self._apply)

    def zoom_in(self):
        if self._pix.isNull(): return
        self._fit = False
        self._scale *= 1.25
        self._scale = min(self._scale, 32.0)
        self._apply()

    def zoom_out(self):
        if self._pix.isNull(): return
        self._fit = False
        self._scale /= 1.25
        self._scale = max(self._scale, 0.05)
        self._apply()

    def fit(self):
        if self._pix.isNull(): return
        self._fit = True
        self._apply()

    def actual(self):
        if self._pix.isNull(): return
        self._fit = False
        self._scale = 1.0
        self._apply()

    def fullscreen(self):
        if self._pix.isNull(): return
        dlg = FullscreenImageDialog(self._pix, self)
        dlg.exec()

class FullscreenImageDialog(QtWidgets.QDialog):
    """Siyah fonda tam ekran, tekerlek zoom + Esc çıkış."""
    def __init__(self, pixmap: QtGui.QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowFlags(QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint)
        self.setModal(True)
        self._pix = pixmap
        self._scale = 1.0
        self._fit = True

        v = QtWidgets.QVBoxLayout(self); v.setContentsMargins(0,0,0,0)
        self.label = QtWidgets.QLabel(alignment=QtCore.Qt.AlignCenter)
        self.label.setStyleSheet("background: black;")
        v.addWidget(self.label)

        # Shortcuts
        QtGui.QShortcut(QtGui.QKeySequence("Esc"), self, self.reject)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl++"), self, self.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+="), self, self.zoom_in)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+-"), self, self.zoom_out)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+0"), self, self.fit)
        QtGui.QShortcut(QtGui.QKeySequence("Ctrl+1"), self, self.actual)

        self.showFullScreen()
        self._apply()

    def wheelEvent(self, e: QtGui.QWheelEvent):
        delta = e.angleDelta().y()
        mods = QtWidgets.QApplication.keyboardModifiers()
        if mods & QtCore.Qt.ControlModifier:
            if delta > 0: self.zoom_in()
            else: self.zoom_out()
            e.accept()
            return
        super().wheelEvent(e)

    def resizeEvent(self, e: QtGui.QResizeEvent):
        super().resizeEvent(e)
        if self._fit:
            self._apply()

    def _apply(self):
        if self._fit:
            avail = self.size()
            if avail.width() > 0 and avail.height() > 0:
                scaled = self._pix.scaled(avail, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
                self.label.setPixmap(scaled)
                return
        w = int(self._pix.width() * self._scale)
        h = int(self._pix.height() * self._scale)
        scaled = self._pix.scaled(w, h, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation)
        self.label.setPixmap(scaled)

    def zoom_in(self):
        self._fit = False
        self._scale = min(self._scale * 1.25, 32.0)
        self._apply()

    def zoom_out(self):
        self._fit = False
        self._scale = max(self._scale / 1.25, 0.05)
        self._apply()

    def fit(self):
        self._fit = True
        self._apply()

    def actual(self):
        self._fit = False
        self._scale = 1.0
        self._apply()

# ----------------- Proje detay -----------------
class ProjectTree(QtWidgets.QTreeView):
    """
    Proje gezgini: sürükle-bırak ile iç taşıma (aynı yere bırakınca kopya YOK),
    dışarıdan dosya kopyalama; sağ tık menüsü: New Note, New Folder, Import Image, Delete.
    """
    request_new_note = QtCore.Signal(Path)
    request_new_dir  = QtCore.Signal(Path)
    request_import_image = QtCore.Signal(Path)
    request_delete   = QtCore.Signal(Path)

    def __init__(self, proj_dir: Path, fs_model: QtWidgets.QFileSystemModel, proxy: QtCore.QSortFilterProxyModel, parent=None):
        super().__init__(parent)
        self.proj_dir = proj_dir
        self._fs_model = fs_model
        self._proxy = proxy

        self.setModel(proxy)
        self.setRootIndex(proxy.mapFromSource(fs_model.index(str(proj_dir))))
        self.setEditTriggers(QtWidgets.QAbstractItemView.EditKeyPressed)
        self.setColumnWidth(0, 260)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)

        # DnD
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragDrop)
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.MoveAction)

    def _path_from_index(self, idx: QtCore.QModelIndex) -> Path:
        if not idx.isValid():
            return self.proj_dir
        src_idx = self._proxy.mapToSource(idx)
        return Path(self._fs_model.filePath(src_idx))

    def _target_dir_for_index(self, idx: QtCore.QModelIndex) -> Path:
        p = self._path_from_index(idx)
        return p if p.is_dir() else p.parent

    # ---- Context Menu ----
    def _ctx_menu(self, pos: QtCore.QPoint):
        idx = self.indexAt(pos)
        target_dir = self._target_dir_for_index(idx)
        menu = QtWidgets.QMenu(self)
        a_new_note = menu.addAction("New Note (.md)")
        a_new_dir  = menu.addAction("New Folder")
        a_img      = menu.addAction("Import Image…")
        menu.addSeparator()
        a_del      = menu.addAction("Delete")
        act = menu.exec(self.viewport().mapToGlobal(pos))
        if act == a_new_note:
            self.request_new_note.emit(target_dir)
        elif act == a_new_dir:
            self.request_new_dir.emit(target_dir)
        elif act == a_img:
            self.request_import_image.emit(target_dir)
        elif act == a_del:
            sel = self.selectedIndexes()
            if sel:
                p = self._path_from_index(sel[0])
                self.request_delete.emit(p)

    # ---- Drag & Drop ----
    def dragEnterEvent(self, e: QtGui.QDragEnterEvent):
        if e.mimeData().hasUrls() or e.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dragMoveEvent(self, e: QtGui.QDragMoveEvent):
        e.acceptProposedAction()

    def dropEvent(self, e: QtGui.QDropEvent):
        idx = self.indexAt(e.position().toPoint())
        target_dir = self._target_dir_for_index(idx)

        # .kaya içine hedeflemeyi önle
        try:
            rel_dst = target_dir.relative_to(self.proj_dir)
            if rel_dst.parts and rel_dst.parts[0].startswith("."):
                e.ignore()
                return
        except Exception:
            pass

        # 1) Dışarıdan bırakılan dosyalar (kopya)
        if e.mimeData().hasUrls():
            for url in e.mimeData().urls():
                src = Path(url.toLocalFile())
                if not src.exists(): continue
                dst = ensure_unique_path(target_dir / src.name)
                try:
                    if src.is_dir():
                        shutil.copytree(src, dst)
                    else:
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, dst)
                except Exception as ex:
                    QtWidgets.QMessageBox.warning(self, "Import", f"Kopyalama hatası:\n{ex}")
            e.acceptProposedAction()
            return

        # 2) Proje içi sürükle-bırak (TAŞIMA) – aynı klasöre bırakılırsa NO-OP
        sel = [self._path_from_index(i) for i in self.selectedIndexes() if i.column() == 0]
        moved_any = False
        for sp in sel:
            if not sp.exists(): continue
            try:
                rel_src = sp.relative_to(self.proj_dir)
                if rel_src.parts and rel_src.parts[0].startswith("."):
                    continue  # .kaya içeriği taşınamaz
            except Exception:
                continue
            if target_dir == sp.parent:
                e.acceptProposedAction()   # aynı klasör: hiçbir işlem yapma
                continue
            if target_dir in sp.parents:
                continue
            try:
                dst = target_dir / sp.name
                if dst.exists():
                    resp = QtWidgets.QMessageBox.question(
                        self, "Move",
                        f"'{dst.name}' zaten var. Üzerine yazılsın mı?",
                        QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No | QtWidgets.QMessageBox.Cancel
                    )
                    if resp == QtWidgets.QMessageBox.Cancel:
                        continue
                    elif resp == QtWidgets.QMessageBox.No:
                        dst = ensure_unique_path(dst)
                shutil.move(str(sp), str(dst))
                moved_any = True
            except Exception as ex:
                QtWidgets.QMessageBox.warning(self, "Move", f"Taşıma hatası:\n{ex}")

        if moved_any:
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

# ----------------- Detay Penceresi -----------------
class ProjectDetail(QtWidgets.QWidget):
    back_requested = QtCore.Signal()
    def __init__(self, proj_dir: Path, meta: dict, parent=None):
        super().__init__(parent)
        self.proj_dir = proj_dir; self.meta = meta
        self._loading_note = False

        outer = QtWidgets.QVBoxLayout(self); outer.setContentsMargins(8,8,8,8); outer.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        back = QtWidgets.QToolButton(text="← Back"); back.setObjectName("navbtn"); back.clicked.connect(self.back_requested.emit)
        title = QtWidgets.QLabel(self.meta.get("name") or proj_dir.name)
        f = title.font(); f.setBold(True); f.setPointSizeF(f.pointSizeF()+2); title.setFont(f)
        top.addWidget(back); top.addSpacing(8); top.addWidget(title); top.addStretch(1)
        outer.addLayout(top)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)

        # Model + Proxy (gizli .kaya'yı ört)
        self.fs_model = QtWidgets.QFileSystemModel(self)
        self.fs_model.setRootPath(str(proj_dir))
        self.fs_model.setReadOnly(False)
        self.proxy = ProjectProxyFilter(proj_dir, self)
        self.proxy.setSourceModel(self.fs_model)

        self.tree = ProjectTree(proj_dir, self.fs_model, self.proxy, self)
        split.addWidget(self.tree)

        # Sağ taraf: Not çalışma alanı + görsel görüntüleyici
        right = QtWidgets.QWidget()
        right_v = QtWidgets.QVBoxLayout(right); right_v.setContentsMargins(0,0,0,0); right_v.setSpacing(6)

        tools = QtWidgets.QHBoxLayout()
        self.file_lbl = QtWidgets.QLabel("overview.md")
        self.file_lbl.setStyleSheet("color:#7CE3C2; font-weight:700;")
        self.btn_attach = QtWidgets.QToolButton(text="Attach")
        self.btn_attach.setObjectName("navbtn")
        self.btn_insert_img = QtWidgets.QToolButton(text="Insert Image")
        self.btn_insert_img.setObjectName("navbtn")
        self.btn_save = QtWidgets.QToolButton(text="Save")
        self.btn_save.setObjectName("navbtn")
        tools.addWidget(self.file_lbl)
        tools.addStretch(1)
        for b in (self.btn_attach, self.btn_insert_img, self.btn_save):
            tools.addWidget(b)
        right_v.addLayout(tools)

        self.stack = QtWidgets.QStackedWidget()
        # 0) Editor workspace (Editor + Preview)
        self.editor_workspace = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        self.editor = QtWidgets.QPlainTextEdit(placeholderText="Proje notu…")
        self.editor.setTabStopDistance(24)
        self.preview = QtWidgets.QTextBrowser()
        self.preview.setOpenExternalLinks(False)
        self.preview.setReadOnly(True)
        self.editor_workspace.addWidget(self.editor)
        self.editor_workspace.addWidget(self.preview)
        self.editor_workspace.setSizes([520, 240])
        self._tm = QtCore.QTimer(self); self._tm.setInterval(600); self._tm.setSingleShot(True)
        self._tm.timeout.connect(self._save)
        self._note_path = proj_dir / "overview.md"
        self.editor.textChanged.connect(self._on_editor_changed)
        self.stack.addWidget(self.editor_workspace)

        # 1) ImageViewer
        self.viewer = ImageViewer(self)
        self.stack.addWidget(self.viewer)

        right_v.addWidget(self.stack, 1)
        split.addWidget(right)
        split.setStretchFactor(0, 2)
        split.setStretchFactor(1, 3)

        outer.addWidget(split, 1)

        # bağlar: tree context menü aksiyonları
        self.tree.request_new_note.connect(self._action_new_note)
        self.tree.request_new_dir.connect(self._action_new_dir)
        self.tree.request_import_image.connect(self._action_import_image)
        self.tree.request_delete.connect(self._action_delete)

        # çift tıklayınca türüne göre aç
        self.tree.doubleClicked.connect(self._open_item)

        self.btn_attach.clicked.connect(self._action_attach_file)
        self.btn_insert_img.clicked.connect(self._action_insert_image)
        self.btn_save.clicked.connect(self._save)

        self._ensure_project_skeleton()
        self._open_note(self._note_path)

    def _ensure_project_skeleton(self):
        for rel in ("notes", "files", "assets/images"):
            (self.proj_dir / rel).mkdir(parents=True, exist_ok=True)
        if not (self.proj_dir / "overview.md").exists():
            (self.proj_dir / "overview.md").write_text(
                f"# {self.meta.get('name') or self.proj_dir.name}\n\n- Hedefler\n- Notlar\n- Sonraki adımlar\n",
                encoding="utf-8"
            )

    def _on_editor_changed(self):
        if self._loading_note:
            return
        self._update_preview()
        self._tm.start()

    def _update_preview(self):
        text = self.editor.toPlainText()
        if self._note_path.suffix.lower() == ".md":
            self.preview.setMarkdown(text)
        else:
            self.preview.setPlainText(text)

    def _open_note(self, p: Path):
        self._note_path = p
        self.file_lbl.setText(str(p.relative_to(self.proj_dir)))
        self._loading_note = True
        try:
            try:
                self.editor.setPlainText(p.read_text(encoding="utf-8"))
            except Exception:
                self.editor.setPlainText("")
            self._update_preview()
            self.stack.setCurrentWidget(self.editor_workspace)
        finally:
            self._loading_note = False

    # --- açma mantığı: metin mi görsel mi? ---
    def _open_item(self, idx: QtCore.QModelIndex):
        src_idx = self.proxy.mapToSource(idx)
        p = Path(self.fs_model.filePath(src_idx))
        if p.is_file() and is_textish_file(p):
            try:
                self._open_note(p)
            except Exception as ex:
                QtWidgets.QMessageBox.warning(self, "Open", f"Açılamadı:\n{ex}")
        elif p.is_file() and is_image_file(p):
            self.viewer.load(p)
            self.stack.setCurrentWidget(self.viewer)
            self.file_lbl.setText(str(p.relative_to(self.proj_dir)))
        else:
            # desteklenmeyen dosya: editörde ham metin olarak göstermeyi deneyebiliriz
            if p.is_file():
                try:
                    self._open_note(p)
                except Exception:
                    QtWidgets.QMessageBox.information(self, "Open", f"Desteklenmeyen biçim: {p.suffix}")
            # klasöre çift tık: hiçbir şey yapma

    def _save(self):
        try:
            self._note_path.parent.mkdir(parents=True, exist_ok=True)
            self._note_path.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.meta["updated_at"] = now_iso()
            write_json(self.proj_dir / META_DIR / META_FILE, self.meta)
        except Exception:
            pass

    # ---- Context actions ----
    def _action_new_note(self, target_dir: Path):
        if target_dir.is_file():
            target_dir = target_dir.parent
        name, ok = QtWidgets.QInputDialog.getText(
            self, "New Note",
            "Note name:"
        )
        if not ok or not name.strip(): return
        path = target_dir / name.strip()
        if path.suffix.lower() != ".md":
            path = path.with_suffix(".md")
        path = safe_child_path(self.proj_dir, path)
        if path is None:
            QtWidgets.QMessageBox.warning(self, "New Note", "Geçersiz yol. Proje dışına çıkılamaz.")
            return
        path = ensure_unique_path(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"# {path.stem}\n", encoding="utf-8")
            self._open_note(path)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "New Note", f"Oluşturulamadı:\n{ex}")

    def _action_new_dir(self, target_dir: Path):
        name, ok = QtWidgets.QInputDialog.getText(self, "New Folder", "Folder name:")
        if not ok or not name.strip(): return
        path = safe_child_path(self.proj_dir, target_dir / name.strip())
        if path is None:
            QtWidgets.QMessageBox.warning(self, "New Folder", "Geçersiz yol. Proje dışına çıkılamaz.")
            return
        path = ensure_unique_path(path)
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "New Folder", f"Oluşturulamadı:\n{ex}")

    def _action_import_image(self, target_dir: Path):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All Files (*.*)"
        )
        if not fn: return
        src = Path(fn)
        dst = ensure_unique_path(target_dir / src.name)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Import Image", f"Kopyalanamadı:\n{ex}")

    def _action_delete(self, path: Path):
        if not path.exists(): return
        # .kaya veya içi → koruma
        try:
            rel = path.relative_to(self.proj_dir)
            if rel.parts and rel.parts[0].startswith("."):
                QtWidgets.QMessageBox.information(self, "Delete", "Bu öğe gizli sistem klasöründe (.kaya).")
                return
        except Exception:
            pass
        if path == self.proj_dir:
            QtWidgets.QMessageBox.information(self, "Delete", "Proje kök dizini bu pencereden silinemez.")
            return
        yn = QtWidgets.QMessageBox.question(self, "Delete", f"Silinsin mi?\n{path}",
                                            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if yn != QtWidgets.QMessageBox.Yes: return
        try:
            if path.is_dir(): shutil.rmtree(path)
            else: path.unlink(missing_ok=True)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Delete", f"Silinemedi:\n{ex}")

    def _action_attach_file(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Attach File", "", "All Files (*.*)")
        if not fn:
            return
        src = Path(fn)
        dst = ensure_unique_path(self.proj_dir / "files" / src.name)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Attach", f"Eklenemedi:\n{ex}")

    def _action_insert_image(self):
        if self.stack.currentWidget() is self.viewer:
            self.stack.setCurrentWidget(self.editor_workspace)
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Insert Image", "", "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp);;All Files (*.*)"
        )
        if not fn:
            return
        src = Path(fn)
        dst = ensure_unique_path(self.proj_dir / "assets" / "images" / src.name)
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            rel = dst.relative_to(self._note_path.parent).as_posix()
            cur = self.editor.textCursor()
            cur.insertText(f"\n![{src.stem}]({rel})\n")
            self.editor.setTextCursor(cur)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Insert Image", f"Eklenemedi:\n{ex}")

# ----------------- Tür klasör karosu (Overview / klasör grid) -----------------
class TypeTile(QtWidgets.QFrame):
    clicked = QtCore.Signal(str)
    def __init__(self, type_key: str, count: int, parent=None):
        super().__init__(parent)
        self.type_key = type_key; self.count = count
        self._w, self._h = 168, 118
        self.setFixedSize(self._w, self._h)
        self.setCursor(QtCore.Qt.ArrowCursor)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.setObjectName("typetile")
        self.setToolTip(type_key.title())
    def sizeHint(self): return QtCore.QSize(self._w, self._h)
    def paintEvent(self, e: QtGui.QPaintEvent):
        p = QtGui.QPainter(self); p.setRenderHint(QtGui.QPainter.Antialiasing, False)
        r = self.rect().adjusted(10, 8, -10, -10)
        accent   = QtGui.QColor(TYPE_COLORS.get(self.type_key, "#00C2C7"))
        neon     = QtGui.QColor(accent).lighter(155)
        dim      = QtGui.QColor(14, 20, 18)
        faint    = QtGui.QColor(0, 0, 0, 90)
        labelfg  = QtGui.QColor("#A0D8C8")
        title_rect = QtCore.QRect(r.left(), r.top(), r.width()-36, 18)
        f = self.font(); f.setBold(True); p.setFont(f)
        p.setPen(neon); p.drawText(title_rect, QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter, self.type_key.title())
        badge = QtCore.QRect(r.right()-20, r.top()+2, 18, 12)
        p.setPen(QtGui.QPen(accent, 1)); p.setBrush(accent.darker(235))
        p.drawRoundedRect(badge, 3, 3); p.setPen(labelfg)
        p.drawText(badge, QtCore.Qt.AlignCenter, str(self.count))
        icon = QtCore.QRect(r.left()+10, r.top()+28, r.width()-20, r.height()-42)
        tab_h = 10
        path_tab = QtGui.QPainterPath()
        path_tab.moveTo(icon.left()+10, icon.top()-tab_h)
        path_tab.lineTo(icon.left()+54, icon.top()-tab_h)
        path_tab.lineTo(icon.left()+44, icon.top())
        path_tab.lineTo(icon.left()+10, icon.top())
        path_tab.closeSubpath()
        body = QtCore.QRect(icon.left(), icon.top(), icon.width(), icon.height())
        path_body = QtGui.QPainterPath(); path_body.addRect(QtCore.QRectF(body))
        p.fillPath(path_body.translated(2, 2), faint)
        p.fillPath(path_body, dim); p.fillPath(path_tab,  dim.darker(115))
        p.setPen(QtGui.QPen(accent, 1)); p.drawPath(path_body); p.drawPath(path_tab)
        p.setPen(QtGui.QPen(neon, 1)); p.drawLine(body.left()+1, body.top()+1, body.right()-1, body.top()+1)
    def mousePressEvent(self, e: QtGui.QMouseEvent):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit(self.type_key)
        super().mousePressEvent(e)

# ----------------- All listesi (tek satır görünüm) -----------------
class AllList(QtWidgets.QTableWidget):
    activated = QtCore.Signal(Path)
    request_delete = QtCore.Signal(Path)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(["Name", "Type", "Status", "Updated"])
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.setSortingEnabled(True)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)
        self.setStyleSheet("QTableWidget { alternate-background-color: rgba(0,255,120,18); }"
                           "QTableWidget::item:selected { background: rgba(0,255,120,55); }")
        self.itemDoubleClicked.connect(self._open)
        # sağ tık ve Del ile silme
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._ctx_menu)
    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if e.key() == QtCore.Qt.Key_Delete:
            p = self._current_path()
            if p: self.request_delete.emit(p); return
        super().keyPressEvent(e)
    def _ctx_menu(self, pos: QtCore.QPoint):
        p = self._current_path()
        if not p: return
        menu = QtWidgets.QMenu(self)
        act_open = menu.addAction("Open")
        act_del  = menu.addAction("Delete Project")
        act = menu.exec(self.viewport().mapToGlobal(pos))
        if act == act_open:
            self.activated.emit(p)
        elif act == act_del:
            self.request_delete.emit(p)
    def _current_path(self) -> Path | None:
        r = self.currentRow()
        if r < 0: return None
        it = self.item(r, 0)
        return it.data(QtCore.Qt.UserRole) if it else None
    def _mk(self, text: str, align=QtCore.Qt.AlignLeft):
        it = QtWidgets.QTableWidgetItem(text)
        it.setTextAlignment(align | QtCore.Qt.AlignVCenter)
        return it
    def populate(self, items: list[tuple[Path, dict]]):
        self.setRowCount(0)
        items = sorted(items, key=lambda x: x[1].get("updated_at",""), reverse=True)
        for d, m in items:
            r = self.rowCount()
            self.insertRow(r)
            name = m.get("name") or d.name
            typ  = m.get("type", "standard")
            st   = m.get("status", "active")
            upd  = m.get("updated_at") or m.get("created_at") or ""
            self.setItem(r, 0, self._mk(name, QtCore.Qt.AlignLeft))
            self.setItem(r, 1, self._mk(typ,  QtCore.Qt.AlignCenter))
            self.setItem(r, 2, self._mk(st,   QtCore.Qt.AlignCenter))
            self.setItem(r, 3, self._mk(upd,  QtCore.Qt.AlignRight))
            self.item(r, 0).setData(QtCore.Qt.UserRole, d)
        if self.rowCount(): self.selectRow(0)
    def _open(self, item: QtWidgets.QTableWidgetItem):
        d = self.item(item.row(), 0).data(QtCore.Qt.UserRole)
        if isinstance(d, Path): self.activated.emit(d)

# ----------------- Ana: ProjectsPage -----------------
class ProjectsPage(QtWidgets.QWidget):
    def __init__(self, projects_dir: Path, fs=None, parent=None):
        super().__init__(parent)
        self.projects_dir = projects_dir; self.fs = fs
        self.templates_dir = (projects_dir.parent / "templates")
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)

        outer = QtWidgets.QVBoxLayout(self); outer.setContentsMargins(8,8,8,8); outer.setSpacing(8)
        self.hdr_wrap = QtWidgets.QWidget()
        hdr = QtWidgets.QHBoxLayout(self.hdr_wrap); hdr.setContentsMargins(0,0,0,0)
        self.btn_over = QtWidgets.QToolButton(text="Overview")
        self.btn_all  = QtWidgets.QToolButton(text="All")
        for b in (self.btn_over, self.btn_all):
            b.setCheckable(True); b.setAutoExclusive(True); b.setObjectName("navbtn")
        self.btn_over.setChecked(True)
        self.search = QtWidgets.QLineEdit(placeholderText="Search (Ctrl+K)")
        self.search.setClearButtonEnabled(True)
        self.new_btn = QtWidgets.QToolButton(text="New Project"); self.new_btn.setObjectName("navbtn")
        hdr.addWidget(self.btn_over); hdr.addWidget(self.btn_all); hdr.addSpacing(10)
        hdr.addWidget(self.search, 1); hdr.addSpacing(10); hdr.addWidget(self.new_btn)
        outer.addWidget(self.hdr_wrap)

        # ana stack: Overview / All
        self.stack = QtWidgets.QStackedWidget(); outer.addWidget(self.stack, 1)

        # OVERVIEW
        self.over_stack = QtWidgets.QStackedWidget()
        self.page_over_grid = QtWidgets.QScrollArea(); self.page_over_grid.setWidgetResizable(True)
        self._grid_wrap = QtWidgets.QWidget(); self._flow = FlowLayout(hspacing=22, vspacing=14)
        self._grid_wrap.setLayout(self._flow); self._grid_wrap.setContentsMargins(24, 10, 24, 20)
        self.page_over_grid.setWidget(self._grid_wrap)
        self.page_over_list = QtWidgets.QWidget()
        ovl = QtWidgets.QVBoxLayout(self.page_over_list); ovl.setContentsMargins(0, 0, 0, 0); ovl.setSpacing(8)
        top = QtWidgets.QHBoxLayout()
        self.back_btn = QtWidgets.QToolButton(text="← Back"); self.back_btn.setObjectName("navbtn")
        self.type_title = QtWidgets.QLabel("Type"); f=self.type_title.font(); f.setBold(True); self.type_title.setFont(f)
        top.addWidget(self.back_btn); top.addSpacing(8); top.addWidget(self.type_title); top.addStretch(1)
        ovl.addLayout(top)
        self.type_list = AllList(); ovl.addWidget(self.type_list, 1)
        self.over_stack.addWidget(self.page_over_grid); self.over_stack.addWidget(self.page_over_list)

        # ALL
        self.page_all = QtWidgets.QWidget()
        all_l = QtWidgets.QVBoxLayout(self.page_all); all_l.setContentsMargins(0,0,0,0); all_l.setSpacing(6)
        self.all_list = AllList(); all_l.addWidget(self.all_list, 1)
        self.stack.addWidget(self.over_stack); self.stack.addWidget(self.page_all)

        self.page_detail = QtWidgets.QWidget()
        self._detail_layout = QtWidgets.QVBoxLayout(self.page_detail)
        self._detail_layout.setContentsMargins(0,0,0,0)
        self._detail_layout.setSpacing(0)
        self._detail_widget = None
        self._list_page_index = 0
        self.stack.addWidget(self.page_detail)

        for view in (self.all_list, self.type_list):
            view.setFocusPolicy(QtCore.Qt.NoFocus)

        self.btn_over.clicked.connect(lambda: self._show_overview())
        self.btn_all.clicked.connect(lambda: self._show_all())
        self.new_btn.clicked.connect(self.new_project)
        self.search.textChanged.connect(self._refresh)
        self.back_btn.clicked.connect(lambda: self.over_stack.setCurrentIndex(0))
        self.type_list.activated.connect(self.open_project)
        self.all_list.activated.connect(self.open_project)
        self.type_list.request_delete.connect(self._delete_project)
        self.all_list.request_delete.connect(self._delete_project)

        self._refresh()

    # ------------- tarama -------------
    def _scan_projects(self):
        out=[]
        if not self.projects_dir.exists(): return out
        for d in sorted(self.projects_dir.iterdir()):
            if not d.is_dir(): continue
            # Öncelik: .kaya/project.json; yoksa kökte project.json (eski projeler)
            meta_path = d / META_DIR / META_FILE
            if not meta_path.exists():
                meta_path = d / META_FILE
            meta=read_json(meta_path, DEFAULT_META)
            if not meta.get("name"): meta["name"]=d.name
            if not meta.get("created_at"): meta["created_at"]=now_iso()
            if not meta.get("updated_at"): meta["updated_at"]=meta["created_at"]
            out.append((d,meta))
        return out

    # ------------- UI yenile -------------
    def _refresh(self):
        projects = self._scan_projects()
        q = (self.search.text() or "").strip().lower()
        if q:
            projects = [(d, m) for d, m in projects
                        if q in (m.get("name", "") + d.name).lower()
                        or q in " ".join(m.get("tags", [])).lower()]
        counts  = {t: 0 for t in TYPE_ORDER}
        buckets = {t: [] for t in TYPE_ORDER}
        for d, m in projects:
            t = m.get("type", "standard")
            counts[t] = counts.get(t, 0) + 1
            buckets.setdefault(t, []).append((d, m))

        # Overview grid
        while self._flow.count():
            it = self._flow.takeAt(0)
            w = it.widget()
            if w:
                w.setParent(None); w.deleteLater()
        for t in TYPE_ORDER:
            tile = TypeTile(t, counts.get(t, 0))
            tile.clicked.connect(lambda _, tt=t, b=list(buckets.get(t, [])): self._open_type_list(tt, b))
            self._flow.addWidget(tile)

        # All list
        self._populate_list(self.all_list, projects)

        if self.over_stack.currentIndex() == 1:
            current_type = self.type_title.text().strip().lower()
            typed = buckets.get(current_type, [])
            if q:
                typed = [(d, m) for d, m in typed
                         if q in (m.get("name", "") + d.name).lower()
                         or q in " ".join(m.get("tags", [])).lower()]
            self._populate_list(self.type_list, typed)

    def _populate_list(self, tbl: AllList, items: list[tuple[Path,dict]]):
        tbl.populate(sorted(items, key=lambda x: x[1].get("updated_at",""), reverse=True))

    # ------------- görünüm geçişleri -------------
    def _show_overview(self):
        self.btn_over.setChecked(True)
        self.stack.setCurrentIndex(0); self.over_stack.setCurrentIndex(0); self._refresh()
    def _show_all(self):
        self.btn_all.setChecked(True)
        self.stack.setCurrentIndex(1); self._refresh()
    def _open_type_list(self, type_key: str, items: list[tuple[Path,dict]]):
        self.type_title.setText(type_key.title())
        self._populate_list(self.type_list, items)
        self.over_stack.setCurrentIndex(1)

    # ------------- yeni proje -------------
    def new_project(self):
        dlg = NewProjectDialog(self.projects_dir, self.templates_dir, self)
        if dlg.exec()!=QtWidgets.QDialog.Accepted: return
        data=dlg.result_data(); name=data["name"]
        if not name:
            QtWidgets.QMessageBox.warning(self,"New Project","Name is required."); return

        # HİBRİT KLASÖR ADI: "Slug — SHORTID"
        folder = f"{slugify(name)} — {shortid(6)}"
        pdir = self.projects_dir / folder
        pdir.mkdir(parents=True, exist_ok=True)

        use_template=data["use_template"]
        tdir=self.templates_dir/data["type"]
        if use_template and tdir.exists(): self._copy_tree(tdir,pdir)

        meta=dict(DEFAULT_META); meta["name"]=name; meta["type"]=data["type"]
        meta["created_at"]=now_iso(); meta["updated_at"]=meta["created_at"]
        (pdir / META_DIR).mkdir(parents=True, exist_ok=True)
        write_json(pdir / META_DIR / META_FILE, meta)
        # Çalışma sayfası iskeleti (boş proje açınca not ekleme hep hazır olsun)
        for rel in ("notes", "files", "assets/images"):
            (pdir / rel).mkdir(parents=True, exist_ok=True)
        (pdir / "overview.md").write_text(
            f"# {name}\n\n- Hedefler\n- Notlar\n- Sonraki adımlar\n",
            encoding="utf-8"
        )
        self._refresh()

    def _copy_tree(self, src: Path, dst: Path):
        for item in src.rglob("*"):
            rel=item.relative_to(src); target=dst/rel
            if item.is_dir(): target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    # ------------- proje aç -------------
    def open_project(self, proj_dir: Path):
        meta_path = proj_dir / META_DIR / META_FILE
        if not meta_path.exists():
            meta_path = proj_dir / META_FILE
        meta=read_json(meta_path, DEFAULT_META)
        self._list_page_index = self.stack.currentIndex()
        if getattr(self, "_detail_widget", None) is not None:
            self._detail_widget.setParent(None)
            self._detail_widget.deleteLater()
        self._detail_widget = ProjectDetail(proj_dir, meta, self)
        self._detail_layout.addWidget(self._detail_widget)
        self._detail_widget.back_requested.connect(self._close_project)
        self.stack.setCurrentWidget(self.page_detail)
        self.hdr_wrap.hide()

    def _close_project(self):
        self.stack.setCurrentIndex(getattr(self, "_list_page_index", 0))
        self.hdr_wrap.show()
        self._refresh()

    # ------------- proje sil -------------
    def _delete_project(self, proj_dir: Path):
        if not proj_dir.exists(): return
        meta_path = proj_dir / META_DIR / META_FILE
        if not meta_path.exists():
            meta_path = proj_dir / META_FILE
        meta = read_json(meta_path, DEFAULT_META)
        name = meta.get("name") or proj_dir.name
        yn = QtWidgets.QMessageBox.question(self, "Delete Project",
                                            f"'{name}' projesi silinsin mi?\n{proj_dir}",
                                            QtWidgets.QMessageBox.Yes|QtWidgets.QMessageBox.No)
        if yn != QtWidgets.QMessageBox.Yes: return
        try:
            shutil.rmtree(proj_dir)
        except Exception as ex:
            QtWidgets.QMessageBox.warning(self, "Delete Project", f"Silinemedi:\n{ex}")
        self._refresh()

# ----------------- Yeni Proje Dialog -----------------
class NewProjectDialog(QtWidgets.QDialog):
    def __init__(self, projects_dir: Path, templates_dir: Path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.projects_dir=projects_dir; self.templates_dir=templates_dir
        v=QtWidgets.QVBoxLayout(self)
        form=QtWidgets.QFormLayout()
        self.name=QtWidgets.QLineEdit(placeholderText="Project name")
        self.type=QtWidgets.QComboBox(); self.type.addItems(TYPE_ORDER)
        self.chk_template=QtWidgets.QCheckBox("Create from template (if available)")
        form.addRow("Name", self.name); form.addRow("Type", self.type); form.addRow("", self.chk_template)
        v.addLayout(form)
        btns=QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok|QtWidgets.QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept); btns.rejected.connect(self.reject); v.addWidget(btns)
    def result_data(self):
        return {"name": self.name.text().strip(),
                "type": self.type.currentText(),
                "use_template": self.chk_template.isChecked()}
