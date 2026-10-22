"""The desktop palette and control styles, kept separate from conversion logic."""

STYLESHEET = """
QWidget#root { background: #F3F5F8; color: #18283E; }
QLabel { color: #18283E; background: transparent; }
QLabel#eyebrow { color: #64758B; font-size: 10px; font-weight: 700; letter-spacing: 2px; }
QLabel#appTitle { color: #15243A; font-size: 27px; font-weight: 600; }
QLabel#appSubtitle { color: #65758A; font-size: 12px; }
QLabel#appVer { color: #64758B; font-size: 11px; }
QFrame#toolbar { background: #FFFFFF; border: 1px solid #DFE5EE; border-radius: 10px; }
QLabel#toolbarHint { color: #64758B; font-size: 12px; }
QPushButton { color: #40516A; background: #FFFFFF; border: 1px solid #DCE3EC;
    border-radius: 6px; padding: 8px 15px; font-size: 12px; font-weight: 600; }
QPushButton:hover { background: #F1F5FA; border-color: #B7C7DA; }
QPushButton:pressed { background: #E7EEF7; }
QPushButton:focus { border-color: #3975D5; }
QPushButton#now { color: #FFFFFF; background: #2864D7; border-color: #2864D7; }
QPushButton#now:hover { background: #2056BB; border-color: #2056BB; }
QPushButton#now:pressed { background: #19499F; }
QPushButton:checked { color: #245BC0; background: #EDF3FF; border-color: #A7BFEF; }
QPushButton#live:checked { color: #167452; background: #EDF8F1; border-color: #A5D5B7; }
QPushButton#clear { border-color: transparent; background: transparent; color: #6C7B90; }
QPushButton#clear:hover { background: #F1F4F8; color: #34465E; }
QFrame#toolbarDivider { background: #E4E9F0; border: none; }
QScrollArea#tableScroll { background: transparent; border: none; }
QWidget#scrollViewport { background: transparent; }
QFrame#conversionTable { background: #FFFFFF; border: 1px solid #DFE5EE; border-radius: 12px; }
QFrame#columnHeader, QFrame#rowLabel, QFrame#valueWrap { background: transparent; border: none; }
QLabel#systemName { color: #203653; font-size: 20px; font-weight: 700; }
QLabel#systemSub { color: #6D7D92; font-size: 11px; }
QLabel#offset { color: #536A86; background: #F0F4F9; border-radius: 4px;
    padding: 3px 7px; font-size: 10px; }
QPushButton#headCopy { border: none; color: #536B8B; background: transparent;
    font-size: 11px; padding: 5px 7px; }
QPushButton#headCopy:hover { background: #EDF3FB; color: #245BC0; }
QLabel#formatHeader { color: #8190A4; font-size: 10px; font-weight: 700; }
QLabel#rowTitle { color: #30445F; font-size: 12px; font-weight: 600; }
QLabel#rowHint { color: #8A97A9; font-size: 10px; }
QFrame#rowDivider { background: #EDF0F5; border: none; max-height: 1px; min-height: 1px; }
QStackedWidget#cellStack, QFrame#comboWrap, QFrame#splitPage { background: transparent; border: none; }
QLineEdit#val, QLineEdit#valSub { color: #253B58; background: #F8FAFD;
    border: 1px solid #E0E7F0; border-radius: 6px; selection-background-color: #D8E6FC;
    selection-color: #173A6C; padding: 9px 10px; }
QLineEdit#valSub { padding: 7px 5px; }
QLineEdit#val:hover, QLineEdit#valSub:hover { border-color: #BDCCDF; }
QLineEdit#val:focus, QLineEdit#valSub:focus { border-color: #407DDD; background: #FFFFFF; }
QLineEdit#val[active="true"], QLineEdit#valSub[active="true"] { border-color: #8AADE5; background: #F1F6FF; }
QLineEdit#val:read-only, QLineEdit#valSub:read-only { color: #5F738D; background: #F2F5F9; }
QLineEdit#val[error="true"], QLineEdit#valSub[error="true"] { color: #A93236; background: #FFF5F4; border-color: #DF9795; }
QLineEdit#val:disabled { color: #97A4B6; background: transparent; border-color: transparent; }
QLabel#subLabel { color: #7B8BA1; font-size: 10px; }
QLabel#tableNote { color: #8390A3; font-size: 10px; }
QFrame#statusBar { background: transparent; border: none; }
QLabel#statusMsg { color: #64758B; font-size: 11px; }
QLabel#statusMsg[level="ok"] { color: #28765B; }
QLabel#statusMsg[level="err"] { color: #B03D42; }
QLabel#footerAuthor { color: #8C98A9; font-size: 10px; }
QScrollBar:vertical { background: #EDF1F6; width: 8px; margin: 0; border-radius: 4px; }
QScrollBar::handle:vertical { background: #C4CFDC; min-height: 28px; border-radius: 4px; }
QScrollBar:horizontal { background: #EDF1F6; height: 8px; margin: 0; border-radius: 4px; }
QScrollBar::handle:horizontal { background: #C4CFDC; min-width: 28px; border-radius: 4px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QToolTip { color: #34465E; background: #FFFFFF; border: 1px solid #DCE3EC; padding: 5px; }
"""
