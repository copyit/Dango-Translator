# -*- coding: utf-8 -*-

from PyQt5.QtCore import *
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import re
import os
import io
import copy
import time
import base64
import shutil
import json
from math import sqrt
import webbrowser
import qtawesome
from PIL import Image, ImageDraw, ImageFile
import traceback
import pyperclip
import pathlib
import natsort

import translator.ocr.dango
import translator.api

import ui.progress_bar
import ui.range
import ui.desc
import ui.static.icon

import utils.translater
import utils.zip
import utils.http
import utils.thread
import utils.message
import utils.sqlite

FONT_PATH_1 = "./config/other/NotoSansSC-Regular.otf"
FONT_PATH_2 = "./config/other/华康方圆体W7.TTC"


# 图片翻译界面
class Manga(QMainWindow) :

    show_error_signal = pyqtSignal(list)
    flushed_render_image_and_text_block_signal = pyqtSignal(str)

    def __init__(self, object) :

        super(Manga, self).__init__()
        self.object = object
        self.logger = object.logger
        self.getInitConfig()
        self.setting_ui = Setting(object)
        self.ui()
        self.trans_edit_ui = TransEdit(object)
        self.flushed_render_image_and_text_block_signal.connect(self.transProcessFlushedRenderImageAndTextBlock)


    def ui(self) :

        # 窗口尺寸
        self.resize(self.window_width*self.rate, self.window_height*self.rate)
        # 窗口标题
        self.setWindowTitle("图片翻译 Ver{}         当前登录用户: {}".format(self.object.yaml["version"], self.object.yaml["user"]))
        # 窗口图标
        self.setWindowIcon(ui.static.icon.APP_LOGO_ICON)
        # 鼠标样式
        self.setCursor(ui.static.icon.PIXMAP_CURSOR)
        # 设置字体
        self.setStyleSheet("font: %spt '%s'; background-color: rgba(255, 255, 255, 1);"%(self.font_size, self.font_type))

        # 底部状态栏
        self.status_label = QLabel(self)
        self.status_label.setStyleSheet("color: #5B8FF9; background-color: #FFFFFF;")

        # 顶部工具栏底色Label
        self.top_background_label = QLabel(self)
        self.top_background_label.setStyleSheet("background-color: #FFFFFF;")

        # 导入原图按钮
        self.input_image_button = QPushButton(self)
        self.input_image_button.setText(" 导入原图")
        self.input_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                              "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                              "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.input_image_button.setIcon(ui.static.icon.OPEN_ICON)
        # 导入原图菜单
        self.input_menu = QMenu(self.input_image_button)
        self.input_menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                                      "QMenu::item:selected:enabled {background: #E5F5FF;}"
                                      "QMenu::item:checked {background: #E5F5FF;}")
        self.input_action_group = QActionGroup(self.input_menu)
        self.input_action_group.setExclusive(True)
        self.refreshInputImageMenu()
        # 将下拉菜单设置为按钮的菜单
        self.input_image_button.setMenu(self.input_menu)
        self.input_action_group.triggered.connect(self.openImageFiles)

        # 一键翻译按钮
        self.trans_all_button = QPushButton(self)
        self.trans_all_button.setText(" 一键翻译")
        self.trans_all_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                            "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                            "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.trans_all_button.setIcon(ui.static.icon.RUN_ICON)
        # 一键翻译菜单
        self.trans_all_menu = QMenu(self.trans_all_button)
        self.trans_all_menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                                          "QMenu::item:selected:enabled {background: #E5F5FF;}"
                                          "QMenu::item:checked {background: #E5F5FF;}")
        self.trans_all_action_group = QActionGroup(self.trans_all_menu)
        self.trans_all_action_group.setExclusive(True)
        self.createTransAllAction("跳过已翻译的")
        self.createTransAllAction("全部重新翻译")
        self.createTransAllAction("只重新翻译并渲染文字")
        self.createTransAllAction("只重新渲染文字")
        # 将下拉菜单设置为按钮的菜单
        self.trans_all_button.setMenu(self.trans_all_menu)
        self.trans_all_action_group.triggered.connect(self.TransAllImages)

        # 译图导出按钮
        self.output_image_button = QPushButton(self)
        self.output_image_button.setText(" 译图导出")
        self.output_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                               "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                               "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.output_image_button.setIcon(ui.static.icon.OUTPUT_ICON)
        # 译图导出菜单
        self.output_menu = QMenu(self.output_image_button)
        self.output_menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                                       "QMenu::item:selected:enabled {background: #E5F5FF;}"
                                       "QMenu::item:checked {background: #E5F5FF;}")
        self.output_action_group = QActionGroup(self.output_menu)
        self.output_action_group.setExclusive(True)
        self.createOutputAction("导出到指定目录")
        self.createOutputAction("导出为压缩包")
        self.createOutputAction("导出工程文件压缩包")
        self.output_menu.addSeparator()
        action = self.createOutputAction("导出后删除过程文件")
        if self.output_is_delete_cache :
            action.setIcon(ui.static.icon.CHECKMARK_ICON)
        else :
            action.setIcon(ui.static.icon.CLOSE_ICON)
        # 将下拉菜单设置为按钮的菜单
        self.output_image_button.setMenu(self.output_menu)
        self.output_action_group.triggered.connect(self.outputImages)

        # 选择语种按钮
        self.select_language_button = QPushButton(self)
        self.select_language_button.setText(" 选择语种")
        self.select_language_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                                  "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                                  "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.select_language_button.setIcon(ui.static.icon.LANGUAGE_ICON)
        # 选择语种菜单
        self.language_menu = QMenu(self.select_language_button)
        self.language_menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                                         "QMenu::item:selected:enabled {background: #E5F5FF;}"
                                         "QMenu::item:checked {background: #E5F5FF;}")
        self.language_action_group = QActionGroup(self.language_menu)
        self.language_action_group.setExclusive(True)
        self.createLanguageAction("日语(Japanese)")
        self.createLanguageAction("英语(English)")
        # 将下拉菜单设置为按钮的菜单
        self.select_language_button.setMenu(self.language_menu)
        self.language_action_group.triggered.connect(self.changeSelectLanguage)

        # 选择翻译源按钮
        self.select_trans_button = QPushButton(self)
        self.select_trans_button.setText(" 选择翻译源")
        self.select_trans_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                               "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                               "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.select_trans_button.setIcon(ui.static.icon.TRANSLATE_ICON)
        # 翻译源菜单
        self.trans_menu = QMenu(self.select_trans_button)
        self.trans_menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                                      "QMenu::item:selected:enabled {background: #E5F5FF;}"
                                      "QMenu::item:checked {background: #E5F5FF;}")
        self.trans_action_group = QActionGroup(self.trans_menu)
        self.trans_action_group.setExclusive(True)
        self.createTransAction("私人团子")
        self.createTransAction("私人彩云")
        self.createTransAction("私人腾讯")
        self.createTransAction("私人百度")
        self.createTransAction("私人ChatGPT")
        self.createTransAction("私人阿里")
        self.createTransAction("私人有道")
        self.createTransAction("私人小牛")
        self.createTransAction("私人火山")
        # 将下拉菜单设置为按钮的菜单
        self.select_trans_button.setMenu(self.trans_menu)
        self.trans_action_group.triggered.connect(self.changeSelectTrans)

        # 高级设置按钮
        self.setting_button = QPushButton(self)
        self.setting_button.setText(" 高级设置")
        self.setting_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                          "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                          "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.setting_button.setIcon(ui.static.icon.SETTING_ICON)
        self.setting_button.clicked.connect(self.setting_ui.show)

        # 购买按钮
        self.buy_button = QPushButton(self)
        self.buy_button.setText(" 去购买使用")
        self.buy_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                      "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                      "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.buy_button.setIcon(ui.static.icon.GO_BUY_ICON)
        self.buy_button.clicked.connect(self.object.settin_ui.openDangoBuyPage)

        # 教程按钮
        self.tutorial_button = QPushButton(self)
        self.tutorial_button.setText(" 使用教程")
        self.tutorial_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                           "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                           "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.tutorial_button.setIcon(ui.static.icon.RUN_ICON)
        self.tutorial_button.clicked.connect(self.openUseTutorial)

        # 列表框按钮底色Label
        self.widget_button_background_label = QLabel(self)
        self.widget_button_background_label.setStyleSheet("background-color: #FFFFFF;")

        # 工具栏横向分割线
        self.cut_line_label1 = QLabel(self)
        self.createCutLine(self.cut_line_label1)

        # 原图按钮
        self.original_image_button = QPushButton(self)
        self.original_image_button.setText("原图")
        self.original_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                                 "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.original_image_button.clicked.connect(lambda: self.clickImageButton("original"))

        # 原图按钮 和 译图按钮 竖向分割线
        self.cut_line_label2 = QLabel(self)
        self.createCutLine(self.cut_line_label2)

        # 编辑按钮
        self.edit_image_button = QPushButton(self)
        self.edit_image_button.setText("编辑")
        self.edit_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                             "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.edit_image_button.clicked.connect(lambda: self.clickImageButton("edit"))

        # 原图按钮 和 译图按钮 竖向分割线
        self.cut_line_label3 = QLabel(self)
        self.createCutLine(self.cut_line_label3)

        # 译图按钮
        self.trans_image_button = QPushButton(self)
        self.trans_image_button.setText("译图")
        self.trans_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                              "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.trans_image_button.clicked.connect(lambda: self.clickImageButton("trans"))

        # 译图右侧竖向分割线
        self.cut_line_label4 = QLabel(self)
        self.createCutLine(self.cut_line_label4)

        # 原图列表框
        self.original_image_widget = CustomListWidget(self)
        self.original_image_widget.setIconSize(QSize(180*self.rate, 180*self.rate))
        self.original_image_widget.itemSelectionChanged.connect(self.loadOriginalImage)
        self.original_image_widget.show()
        self.original_image_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.original_image_widget.customContextMenuRequested.connect(self.showOriginalListWidgetMenu)
        self.original_image_widget.setSpacing(5)
        self.setAcceptDrops(True)

        # 编辑图列表框
        self.edit_image_widget = CustomListWidget(self)
        self.edit_image_widget.setIconSize(QSize(180*self.rate, 180*self.rate))
        self.edit_image_widget.itemSelectionChanged.connect(self.loadEditImage)
        self.edit_image_widget.hide()
        self.edit_image_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.edit_image_widget.customContextMenuRequested.connect(self.showEditListWidgetMenu)
        self.edit_image_widget.setSpacing(5)

        # 译图列表框
        self.trans_image_widget = CustomListWidget(self)
        self.trans_image_widget.setIconSize(QSize(180*self.rate, 180*self.rate))
        self.trans_image_widget.itemSelectionChanged.connect(self.loadTransImage)
        self.trans_image_widget.hide()
        self.trans_image_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.trans_image_widget.customContextMenuRequested.connect(self.showTransListWidgetMenu)
        self.trans_image_widget.setSpacing(5)

        # 批量删除按钮上方横向分割线
        self.cut_line_label5 = QLabel(self)
        self.createCutLine(self.cut_line_label5)

        # 批量删除按钮
        self.delete_button = QPushButton(self)
        self.delete_button.setText("批量删除")
        self.delete_button.setStyleSheet("QPushButton {background: #FFFFFF; color: #5B8FF9;}"
                                         "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.delete_button.clicked.connect(lambda: self.removeItemWidget(self.click_button_type))
        self.delete_button.setToolTip("<b>按住Ctrl键可以多选列表框的图片, 然后批量删除</b>")

        # 全部删除按钮
        self.all_delete_button = QPushButton(self)
        self.all_delete_button.setText("全部删除")
        self.all_delete_button.setStyleSheet("QPushButton {background: #FFFFFF; color: #5B8FF9;}"
                                             "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.all_delete_button.clicked.connect(self.clearAllImages)
        self.all_delete_button.setToolTip("<b>删除列表框所有图片</b>")

        # 图片大图展示
        self.show_image_scroll_area = CustomScrollArea(self)
        self.show_image_scroll_area.setWidgetResizable(True)
        self.show_image_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show_image_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.show_image_scroll_area.setStyleSheet("background-color: #FFFFFF;")

        # 错误展示提示窗
        self.show_error_label = QPushButton(self)
        self.show_error_label.setIcon(ui.static.icon.ERROR_ICON)
        self.show_error_label.hide()
        self.show_error_signal.connect(self.showError)

        # 隐藏图片列表框按钮
        self.hide_image_widget_button = CustomButton(self)
        self.hide_image_widget_button.setHideStatus(True, ui.static.icon.LAST_PAGE_ICON)
        self.hide_image_widget_button.clicked.connect(self.hideImageWidget)

        # 上一页按钮
        self.last_page_button = CustomButton(self)
        self.last_page_button.setIcon(ui.static.icon.LAST_PAGE_ICON)
        self.last_page_button.setShortcut(QKeySequence(Qt.Key_Up))
        self.last_page_button.clicked.connect(lambda: self.changeImageListPosition("last"))

        # 下一页按钮
        self.next_page_button = CustomButton(self)
        self.next_page_button.setIcon(ui.static.icon.NEXT_PAGE_ICON)
        self.next_page_button.setShortcut(QKeySequence(Qt.Key_Down))
        self.next_page_button.clicked.connect(lambda: self.changeImageListPosition("next"))

        # 左右切换原图/编辑图/译图快捷键
        shortcut = QShortcut(QKeySequence(Qt.Key_Left), self)
        shortcut.activated.connect(lambda: self.switchImageWidget("left"))
        shortcut = QShortcut(QKeySequence(Qt.Key_Right), self)
        shortcut.activated.connect(lambda: self.switchImageWidget("right"))

        # 导入图片进度条
        self.input_images_progress_bar = ui.progress_bar.ProgressBar(self.object.yaml["screen_scale_rate"], "input_images")
        # 图片翻译进度条
        self.trans_process_bar = ui.progress_bar.MangaProgressBar(self.object.yaml["screen_scale_rate"])

        # 背景图片
        self.background_label = TransparentImageLabel(self)
        self.background_label.setAlignment(Qt.AlignCenter)
        self.background_label.setPixmap(ui.static.icon.MANGA_PIXMAP)
        self.show_image_scroll_area.setWidget(self.background_label)
        self.background_label.setOpacity(0.7)

        # 刷新底部状态栏
        self.refreshStatusLabel()
        # 初始化点击原图按钮
        self.original_image_button.click()


    # 初始化配置
    def getInitConfig(self) :

        # 界面缩放比例
        self.rate = self.object.yaml["screen_scale_rate"]
        # 界面字体
        self.font_type = "华康方圆体W7"
        # 字体颜色(蓝色)
        self.color = "#5B8FF9"
        # 界面字体大小
        self.font_size = 7
        # 界面尺寸
        self.window_width = 1200
        self.window_height = 700
        # 图片路径列表
        self.image_path_list = []
        # 当前图片列表框的索引
        self.image_widget_index = 0
        # 当前图片列表框的滑块坐标
        self.image_widget_scroll_bar_value = 0
        # 渲染文本块的组件列表
        self.render_text_block_label = []
        # 语种映射表
        self.language_map = {
            "JAP": "日语(Japanese)",
            "ENG": "英语(English)",
            "RUS": "韩语(Korean)",
            "KOR": "俄语(Russian)",
        }
        # 试用开关
        self.check_permission = False
        # 是否进行试用检测
        self.is_check_permission_sign = False
        # 接口试用次数
        self.manga_read_count = -1
        # 对于Image库format格式类型映射
        self.image_ext_map = {
            "jpg": "JPEG",
            "JPG": "JPEG",
            "jpeg": "JPEG",
            "JPEG": "JPEG",
            "png": "PNG",
            "PNG": "PNG",
            "webp": "WEBP",
            "WEBP": "WEBP"
        }
        # 隐藏图片列表框状态, True-隐藏, False-不隐藏
        self.hide_image_widget_status = False
        self.show_image_widget = None
        self.show_error_sign = False
        self.click_button_type = "original"
        # 使用有效期
        self.valid_time = "-"
        # 保存的历史路径最大长度
        self.manga_dir_paths_max_length = 10
        # 保存的历史打开路径
        self.manga_dir_paths = []
        manga_dir_path = self.object.yaml.get("manga_dir_path", [])
        # 兼容旧版本以字符串保存的单组路径
        if type(manga_dir_path) == str :
            self.manga_dir_paths.insert(0, manga_dir_path)
        elif type(manga_dir_path) == list :
            self.manga_dir_paths = manga_dir_path
        # 去重
        self.manga_dir_paths = list(set(self.manga_dir_paths))
        # 最大保存
        if len(self.manga_dir_paths) > self.manga_dir_paths_max_length :
            self.manga_dir_paths = self.manga_dir_paths[:self.manga_dir_paths_max_length]
        self.object.yaml["manga_dir_path"] = self.manga_dir_paths
        # 导出后是否删除过程文件
        self.output_is_delete_cache = False
        # 导入时是否清空列表框
        self.manga_input_clear_use = True


    # 根据分辨率定义控件位置尺寸
    def customSetGeometry(self, object, x, y, w, h, w_rate=1, h_rate=1):

        object.setGeometry(QRect(
            int(x * w_rate),
            int(y * w_rate),
            int(w * h_rate),
            int(h * h_rate))
        )


    # 绘制一条分割线
    def createCutLine(self, label) :

        label.setFrameShadow(QFrame.Raised)
        label.setFrameShape(QFrame.Box)
        label.setStyleSheet("border-width: 1px; "
                            "border-style: solid; "
                            "border-color: rgba(62, 62, 62, 0.2);")


    # 点击隐藏图片列表框按钮信号槽
    def hideImageWidget(self) :

        self.hide_image_widget_status = not self.hide_image_widget_status
        if self.hide_image_widget_status :
            # 隐藏图片列表框
            self.original_image_button.hide()
            self.edit_image_button.hide()
            self.trans_image_button.hide()
            self.original_image_widget.hide()
            self.edit_image_widget.hide()
            self.trans_image_widget.hide()
            self.cut_line_label2.hide()
            self.cut_line_label3.hide()
            self.cut_line_label4.hide()
            self.hide_image_widget_button.move(0, self.hide_image_widget_button.y())
            self.show_image_scroll_area.setGeometry(
                0, self.show_image_scroll_area.y(), self.width(),
                self.show_image_scroll_area.height()
            )
            self.last_page_button.move(self.last_page_button.x()-self.cut_line_label4.x(), self.last_page_button.y())
            self.hide_image_widget_button.setHideStatus(True, ui.static.icon.NEXT_PAGE_ICON)
            self.hide_image_widget_button.setIcon(ui.static.icon.NEXT_PAGE_ICON)
        else :
            # 显示图片列表框
            self.original_image_button.show()
            self.edit_image_button.show()
            self.trans_image_button.show()
            self.original_image_widget.show()
            self.edit_image_widget.show()
            self.trans_image_widget.show()
            self.cut_line_label2.show()
            self.cut_line_label3.show()
            self.cut_line_label4.show()
            self.show_image_scroll_area.setGeometry(
                self.cut_line_label4.x(), self.show_image_scroll_area.y(),
                self.width()-self.cut_line_label4.x(), self.show_image_scroll_area.height()
            )
            self.last_page_button.move(self.last_page_button.x()+self.cut_line_label4.x(), self.last_page_button.y())
            self.hide_image_widget_button.move(self.cut_line_label4.x(), self.hide_image_widget_button.y())
            self.hide_image_widget_button.setHideStatus(True, ui.static.icon.LAST_PAGE_ICON)
            self.hide_image_widget_button.setIcon(ui.static.icon.LAST_PAGE_ICON)


    # 上一页下一页按钮信号槽
    def changeImageListPosition(self, sign) :

        if len(self.image_path_list) == 0 :
            return

        image_widget = self.original_image_widget
        if self.click_button_type == "edit" :
            image_widget = self.edit_image_widget
        elif self.click_button_type == "trans" :
            image_widget = self.trans_image_widget

        row = image_widget.currentRow()
        if sign == "next" :
            if row < len(self.image_path_list) - 1 :
                image_widget.setCurrentRow(row + 1)
        else :
            if row > 0 :
                image_widget.setCurrentRow(row -1)


    # 从文件导入
    def inputImageFromFile(self, init_path) :

        images, _ = QFileDialog.getOpenFileNames(
            self,
            "选择要翻译的生肉漫画原图（可多选）",
            init_path,
            "图片类型(*.png *.jpg *.jpeg *.webp);;所有类型 (*)",
            options=QFileDialog.Options()
        )
        return images


    # 从文件夹导入
    def inputImageFromDir(self, init_path) :

        images = []
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "选择要翻译的生肉漫画目录",
            init_path,
            options=QFileDialog.Options()
        )
        # 检查目录
        if not os.path.exists(folder_path) :
            utils.message.MessageBox("导入图片失败", "不存在的目录     ")
            return images
        if os.path.basename(folder_path) == "dango_manga" :
            utils.message.MessageBox("导入图片失败", "不能选择dango_manga目录     ")
            return images
        if "dango_manga" in folder_path and os.path.basename(folder_path) == "tmp" :
            utils.message.MessageBox("导入图片失败", "不能选择tmp目录     ")
            return images
        # 获取目录下所有图片加入列表
        for file in os.listdir(folder_path) :
            # 过滤非图片文件
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext != ".png" and file_ext != ".jpg" and file_ext != ".jpeg" and file_ext != ".webp" :
                continue
            images.append(os.path.join(folder_path, file))

        return images


    # 从多文件夹导入
    def inputImageFromBatchDir(self) :

        images = []
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        l = file_dialog.findChild(QListView, "listView")
        if l :
            l.setSelectionMode(QAbstractItemView.MultiSelection)
        t = file_dialog.findChild(QTreeView)
        if t :
            t.setSelectionMode(QAbstractItemView.MultiSelection)
        file_dialog.setFilter(QDir.Dirs)
        if file_dialog.exec_() == QDialog.Accepted:
            folder_paths = file_dialog.selectedFiles()
            # 遍历多个文件夹
            for folder_path in folder_paths[1:] :
                if not os.path.exists(folder_path) :
                    utils.message.MessageBox("导入图片失败", "不存在的目录     ")
                    return []
                if os.path.basename(folder_path) == "dango_manga" :
                    utils.message.MessageBox("导入图片失败", "不能选择dango_manga目录     ")
                    return []
                if "dango_manga" in folder_path and os.path.basename(folder_path) == "tmp" :
                    utils.message.MessageBox("导入图片失败", "不能选择tmp目录     ")
                    return []
                for file in os.listdir(folder_path) :
                    # 过滤非图片文件
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext != ".png" and file_ext != ".jpg" and file_ext != ".jpeg" and file_ext != ".webp" :
                        continue
                    images.append(os.path.join(folder_path, file))

        return images


    # 从历史目录里直接导入
    def inputImageFromHistoryPath(self, folder_path) :

        images = []
        # 路径校验
        if not os.path.exists(folder_path):
            utils.message.MessageBox("导入图片失败", "不存在的目录     ")
            return images
        if os.path.basename(folder_path) == "dango_manga" :
            utils.message.MessageBox("导入图片失败", "不能选择dango_manga目录     ")
            return images
        if "dango_manga" in folder_path and os.path.basename(folder_path) == "tmp" :
            utils.message.MessageBox("导入图片失败", "不能选择tmp目录     ")
            return images
        for file in os.listdir(folder_path) :
            # 过滤非图片文件
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext != ".png" and file_ext != ".jpg" and file_ext != ".jpeg" and file_ext != ".webp":
                continue
            images.append(os.path.join(folder_path, file))

        return images


    # 打开图片文件列表
    def openImageFiles(self, action) :

        if action.data() == "每次导入清除已导入的图片" :
            self.manga_input_clear_use = not self.manga_input_clear_use
            if self.manga_input_clear_use :
                action.setIcon(ui.static.icon.CHECKMARK_ICON)
            else :
                action.setIcon(ui.static.icon.CLOSE_ICON)
            return

        # 最近一次打开的目录
        init_path = os.getcwd()
        if len(self.manga_dir_paths) > 0 :
            init_path = self.manga_dir_paths[0]

        images = []
        if action.data() == "从文件导入" :
            images = self.inputImageFromFile(init_path)
        elif action.data() == "从文件夹导入" :
            images = self.inputImageFromDir(init_path)
        elif action.data() == "从多个文件夹导入" :
            images = self.inputImageFromBatchDir()
        elif action.data() in self.manga_dir_paths :
            images = self.inputImageFromHistoryPath(action.data())
        else :
            return

        if not images :
            return

        dir_paths = []
        # 校验是否有过长的路径
        for file_path in images :
            file_name = os.path.basename(file_path)
            base_path = os.path.dirname(file_path)
            if base_path not in dir_paths :
                dir_paths.append(base_path)
            check_file_path = os.path.join(base_path, "dango_manga", "tmp", file_name)
            if len(check_file_path) >= 250 :
                utils.message.MessageBox("导入图片失败", "文件地址过长:\n%s"%file_path)
                return

        if images :
            # 清除所有图片
            if self.manga_input_clear_use :
                self.clearAllImages()
            # 根据文件名排序
            images = self.dirFilesPathSort(images)
            # 进度条窗口
            self.input_images_progress_bar.modifyTitle("导入图片 -- 加载中请勿关闭此窗口")
            self.input_images_progress_bar.show()
            # 导入图片线程
            thread = utils.thread.createInputImagesQThread(self, images)
            thread.bar_signal.connect(self.input_images_progress_bar.paintProgressBar)
            thread.image_widget_signal.connect(self.inputImage)
            utils.thread.runQThread(thread)

        # 记忆上次操作的目录
        for dir_path in dir_paths :
            if dir_path in self.manga_dir_paths :
                self.manga_dir_paths.remove(dir_path)
            self.manga_dir_paths.insert(0, dir_path)
        if len(self.manga_dir_paths) > self.manga_dir_paths_max_length :
            self.manga_dir_paths = self.manga_dir_paths[:self.manga_dir_paths_max_length]
        self.object.yaml["manga_dir_path"] = self.manga_dir_paths
        # 刷新原图导入按钮的菜单栏
        self.refreshInputImageMenu()


    # 一键翻译
    def TransAllImages(self, action) :

        if action.data() == "跳过已翻译的" :
            self.clickTransAllButton("pass")
        elif action.data() == "全部重新翻译" :
            self.clickTransAllButton("all")
        elif action.data() == "只重新翻译并渲染文字" :
            self.clickTransAllButton("rdr")
        elif action.data() == "只重新渲染文字" :
            self.clickTransAllButton("rdr")
        else :
            return


    # 导出译图文件
    def outputImages(self, action) :

        if action.data() == "导出后删除过程文件" :
            self.output_is_delete_cache = not self.output_is_delete_cache
            if self.output_is_delete_cache :
                action.setIcon(ui.static.icon.CHECKMARK_ICON)
            else:
                action.setIcon(ui.static.icon.CLOSE_ICON)
            return

        try :
            output_image_list = []
            folder_name = "dango-%s"%(time.time())
            base_path = ""

            for image_path in self.image_path_list :
                rdr_image_path = self.getRdrFilePath(image_path)
                if os.path.exists(rdr_image_path) :
                    output_image_list.append(rdr_image_path)
                    folder_name = os.path.basename(os.path.dirname(image_path))
                    base_path = os.path.dirname(image_path)
            if len(output_image_list) == 0 :
                return utils.message.MessageBox("导出失败", "没有可以导出的译图文件      ")

            # 选择指定位置
            options = QFileDialog.Options()
            dialog = QFileDialog()
            try :
                # 默认桌面
                dialog.setDirectory(QStandardPaths.standardLocations(QStandardPaths.DesktopLocation)[0])
            except Exception :
                # 默认用户根目录
                dialog.setDirectory(QDir.homePath())
            folder_path = dialog.getExistingDirectory(self, "选择要导出的位置", "", options=options)
            if not os.path.exists(folder_path):
                return utils.message.MessageBox("导出失败", "无效的目录      ")

            if action.data() == "导出到指定目录" :
                # 新建导出文件夹
                folder_path = os.path.join(folder_path, folder_name)
                if not os.path.exists(folder_path) :
                    os.mkdir(folder_path)
                # 复制完成的rdr图片
                for index, image_path in enumerate(output_image_list) :
                    if self.object.config.get("mangaOutputRenameUse", False) :
                        new_image_path = os.path.join(folder_path, "%d.png"%(index+1))
                    else :
                        new_image_path = os.path.join(folder_path, os.path.basename(image_path))
                    shutil.copy(image_path, new_image_path)

            elif action.data() == "导出为压缩包" :
                # 压缩包名称
                zip_name = "{}.zip".format(folder_name)
                zip_path = os.path.join(folder_path, zip_name)
                # 是否重命名文件
                if self.object.config.get("mangaOutputRenameUse", False) :
                    # 新建导出文件夹
                    folder_path = os.path.join(folder_path, folder_name)
                    if not os.path.exists(folder_path):
                        os.mkdir(folder_path)
                    # 复制完成的rdr图片
                    new_image_list = []
                    for index, image_path in enumerate(output_image_list):
                        new_image_path = os.path.join(folder_path, "%d.png"%(index+1))
                        new_image_list.append(new_image_path)
                        shutil.copy(image_path, new_image_path)
                    utils.zip.zipFiles(new_image_list, zip_path)
                    shutil.rmtree(folder_path)
                else :
                    utils.zip.zipFiles(output_image_list, zip_path)

            elif action.data() == "导出工程文件压缩包" :
                zip_name = "{}.zip".format(folder_name)
                zip_path = os.path.join(folder_path, zip_name)
                utils.zip.zipDirectory(base_path, zip_path)

            else :
                return

            # 删除过程文件
            if self.output_is_delete_cache :
                delete_dir_list = []
                for image_path in self.image_path_list :
                    dango_manga_path, _ = self.getDangoMangaPath(image_path)
                    delete_dir_list.append(dango_manga_path)
                delete_dir_list = list(set(delete_dir_list))
                for delete_dir in delete_dir_list :
                    shutil.rmtree(delete_dir)


        except Exception :
            self.logger.error(traceback.format_exc())

        os.startfile(folder_path)


    # 导入图片
    def inputImage(self, index, image_path, finish_sign) :

        if not finish_sign :
            # 图片添加至原图列表框
            self.originalImageWidgetAddImage(index, image_path)
            # 图片添加至编辑图列表框
            self.editImageWidgetAddImage(index)
            if os.path.exists(self.getRdrFilePath(image_path)) :
                self.editImageWidgetRefreshImage(image_path)
            # 图片添加至译图列表框
            self.transImageWidgetAddImage(index)
            if os.path.exists(self.getRdrFilePath(image_path)) :
                self.transImageWidgetRefreshImage(image_path)

        else :
            # 跳转到原图栏
            self.original_image_button.click()
            self.original_image_widget.setCurrentRow(0)
            self.loadOriginalImage()
            self.input_images_progress_bar.close()


    # 文件列表排序
    def dirFilesPathSort(self, files) :

        try :
            new_files = natsort.natsorted(files, key=lambda x: os.path.splitext(x)[1])
        except Exception :
            tmp_dict = {}
            for file_path in files :
                if len(file_path) not in tmp_dict:
                    tmp_dict[len(file_path)] = []
                tmp_dict[len(file_path)].append(file_path)

            new_files = []
            for k in sorted(tmp_dict.keys()):
                for val in sorted(tmp_dict[k]):
                    new_files.append(val)

        return new_files


    # 清除所有图片
    def clearAllImages(self) :

        self.original_image_widget.clear()
        self.edit_image_widget.clear()
        self.trans_image_widget.clear()
        self.image_path_list.clear()


    # 点击 原图/编辑/译图 按钮
    def clickImageButton(self, button_type) :

        self.click_button_type = button_type
        self.original_image_widget.hide()
        self.edit_image_widget.hide()
        self.trans_image_widget.hide()
        self.original_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                                 "QPushButton:hover {background-color: #83AAF9; color: #000000;}")
        self.edit_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                             "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        self.trans_image_button.setStyleSheet("QPushButton {background: transparent; color: #5B8FF9;}"
                                              "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}")
        if button_type == "original" :
            self.original_image_widget.show()
            self.original_image_button.setStyleSheet("background-color: #83AAF9; color: #FFFFFF;")
            self.original_image_widget.verticalScrollBar().setValue(self.image_widget_scroll_bar_value)
            self.original_image_widget.setCurrentRow(self.image_widget_index)
            self.loadOriginalImage()

        elif button_type == "edit" :
            self.edit_image_widget.show()
            self.edit_image_button.setStyleSheet("background-color: #83AAF9; color: #FFFFFF;")
            self.edit_image_widget.verticalScrollBar().setValue(self.image_widget_scroll_bar_value)
            self.edit_image_widget.setCurrentRow(self.image_widget_index)
            self.loadEditImage()

        elif button_type == "trans" :
            self.trans_image_widget.show()
            self.trans_image_button.setStyleSheet("background-color: #83AAF9; color: #FFFFFF;")
            self.trans_image_widget.verticalScrollBar().setValue(self.image_widget_scroll_bar_value)
            self.trans_image_widget.setCurrentRow(self.image_widget_index)
            self.loadTransImage()


    # 创建导入原图按钮的下拉菜单
    def createInputAction(self, label) :

        action = QAction(label, self.input_menu)
        action.setCheckable(False)
        action.setData(label)
        self.input_action_group.addAction(action)
        self.input_menu.addAction(action)

        return action


    # 刷新导入原图按钮的下拉菜单选项
    def refreshInputImageMenu(self) :

        self.input_menu.clear()
        self.createInputAction("从文件导入")
        self.createInputAction("从文件夹导入")
        self.createInputAction("从多个文件夹导入")
        # 历史路径
        if len(self.manga_dir_paths) > 0 :
            self.input_menu.addSeparator()
        for path in self.manga_dir_paths :
            self.createInputAction(path)
        # 是否清空列表框
        self.input_menu.addSeparator()
        action = self.createInputAction("每次导入清除已导入的图片")
        if self.manga_input_clear_use :
            action.setIcon(ui.static.icon.CHECKMARK_ICON)
        else :
            action.setIcon(ui.static.icon.CLOSE_ICON)


    # 创建一键翻译按钮的下拉菜单
    def createTransAllAction(self, label) :

        action = QAction(label, self.trans_all_menu)
        action.setCheckable(False)
        action.setData(label)
        self.trans_all_action_group.addAction(action)
        self.trans_all_menu.addAction(action)

        return action


    # 创建译图导出按钮的下拉菜单
    def createOutputAction(self, label) :

        action = QAction(label, self.output_menu)
        action.setCheckable(False)
        action.setData(label)
        self.output_action_group.addAction(action)
        self.output_menu.addAction(action)

        return action


    # 创建语种按钮的下拉菜单
    def createLanguageAction(self, label) :

        action = QAction(label, self.language_menu)
        action.setCheckable(True)
        action.setData(label)
        self.language_action_group.addAction(action)
        self.language_menu.addAction(action)
        if self.language_map[self.object.config["mangaLanguage"]] == label :
            action.setChecked(True)

        return action


    # 创建翻译源按钮的下拉菜单
    def createTransAction(self, label) :

        action = QAction(label, self.trans_menu)
        action.setCheckable(True)
        action.setData(label)
        self.trans_action_group.addAction(action)
        self.trans_menu.addAction(action)
        if self.object.config["mangaTrans"] == label :
            action.setChecked(True)

        return action


    # 改变所使用的语种
    def changeSelectLanguage(self, action) :

        tmp_map = {}
        for k, v in self.language_map.items() :
            tmp_map[v] = k
        self.object.config["mangaLanguage"] = tmp_map[action.data()]
        self.refreshStatusLabel()


    # 改变所使用的翻译源
    def changeSelectTrans(self, action) :

        self.object.config["mangaTrans"] = action.data()
        self.refreshStatusLabel()


    # 刷新底部状态栏信息
    def refreshStatusLabel(self, image_path="") :

        # 计算当前页码
        index = 0
        if image_path in self.image_path_list :
            index = self.image_path_list.index(image_path) + 1

        if self.check_permission :
            self.status_label.setText(
                '<font color="#5B8FF9">&nbsp;&nbsp;原文语种:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;翻译源:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;试用开关:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;剩余试用次数:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;当前页数:&nbsp;</font> <font color="#708090">{}/{}</font>'
                .format(
                    self.language_map[self.object.config["mangaLanguage"]],
                    self.object.config["mangaTrans"],
                    "打开",
                    self.manga_read_count,
                    index,
                    len(self.image_path_list),
                ))
        else :
            self.status_label.setText(
                '<font color="#5B8FF9">&nbsp;&nbsp;原文语种:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;翻译源:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;试用开关:&nbsp;</font> <font color="#708090">{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;当前页数:&nbsp;</font> <font color="#708090">{}/{}</font>'
                '<font color="#5B8FF9">&nbsp;&nbsp;&nbsp;有效期截止:&nbsp;</font> <font color="#708090">{}</font>'
                .format(
                    self.language_map[self.object.config["mangaLanguage"]],
                    self.object.config["mangaTrans"],
                    "关闭",
                    index,
                    len(self.image_path_list),
                    self.valid_time
                ))


    # 设置原图列表框右键菜单
    def showOriginalListWidgetMenu(self, pos) :

        item = self.original_image_widget.itemAt(pos)
        if item is not None:
            menu = QMenu(self)
            menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                               "QMenu::item:selected:enabled {background: #E5F5FF;}"
                               "QMenu::item:checked {background: #E5F5FF;}")
            # 添加菜单项
            translater_action = menu.addAction("翻译当前图片")
            translater_action.triggered.connect(lambda: self.translaterItemWidget(item, "original"))
            delete_action = menu.addAction("移除当前图片")
            delete_action.triggered.connect(lambda: self.removeItemWidget("original"))
            # 显示菜单
            cursorPos = QCursor.pos()
            menu.exec_(cursorPos)


    # 设置编辑列表框右键菜单
    def showEditListWidgetMenu(self, pos) :

        item = self.edit_image_widget.itemAt(pos)
        if item is not None:
            menu = QMenu(self)
            menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                               "QMenu::item:selected:enabled {background: #E5F5FF;}"
                               "QMenu::item:checked {background: #E5F5FF;}")
            # 添加菜单项
            translater_action = menu.addAction("翻译当前图片")
            translater_action.triggered.connect(lambda: self.translaterItemWidget(item, "edit"))
            delete_action = menu.addAction("移除当前图片")
            delete_action.triggered.connect(lambda: self.removeItemWidget("edit"))
            # 显示菜单
            cursorPos = QCursor.pos()
            menu.exec_(cursorPos)


    # 设置译图列表框右键菜单
    def showTransListWidgetMenu(self, pos):

        item = self.trans_image_widget.itemAt(pos)
        if item is not None:
            menu = QMenu(self)
            menu.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                               "QMenu::item:selected:enabled {background: #E5F5FF;}"
                               "QMenu::item:checked {background: #E5F5FF;}")
            # 添加菜单项
            output_action = menu.addAction("另存为")
            output_action.triggered.connect(lambda: self.saveImageItemWidget(item))
            # 显示菜单
            cursorPos = QCursor.pos()
            menu.exec_(cursorPos)


    # 译图框保存图片
    def saveImageItemWidget(self, item) :

        row = self.trans_image_widget.indexFromItem(item).row()
        image_path = self.image_path_list[row]

        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self,
                                                   "译图另存为",
                                                   image_path,
                                                   "图片类型(*.png *.jpg *.jpeg);;所有类型 (*)",
                                                   options=options)
        if file_path :
            shutil.copy(self.getRdrFilePath(image_path), file_path)


    # 列表框右键菜单删除子项
    def removeItemWidget(self, item_type) :

        if item_type == "edit" :
            items = self.edit_image_widget.selectedItems()
        elif item_type == "trans" :
            items = self.trans_image_widget.selectedItems()
        else :
            items = self.original_image_widget.selectedItems()

        for item in items :
            if item_type == "edit" :
                row = self.edit_image_widget.indexFromItem(item).row()
            elif item_type == "trans" :
                row = self.trans_image_widget.indexFromItem(item).row()
            else :
                row = self.original_image_widget.indexFromItem(item).row()
            if row > (len(self.image_path_list) - 1) :
                continue
            # 列表框删除图片
            self.original_image_widget.takeItem(row)
            self.edit_image_widget.takeItem(row)
            self.trans_image_widget.takeItem(row)
            self.image_path_list.pop(row)


    # 原图列表框添加图片
    def originalImageWidgetAddImage(self, index, image_path) :

        pixmap = self.fromImageToPixmap(image_path)
        pixmap = pixmap.scaled(180*self.rate, 180*self.rate, aspectRatioMode=Qt.KeepAspectRatio)
        item = QListWidgetItem(self.original_image_widget)
        item.setText(index)
        item.setIcon(QIcon(pixmap))
        item.listWidget()
        self.original_image_widget.addItem(item)
        image_path = os.path.normpath(image_path)
        self.image_path_list.append(image_path)


    # 编辑图列表框添加图片
    def editImageWidgetAddImage(self, index) :

        item = QListWidgetItem(self.edit_image_widget)
        pixmap = self.createTransparentPixmap(180*self.rate, 180*self.rate)
        item.setText(index)
        item.setIcon(QIcon(pixmap))
        item.listWidget()
        self.edit_image_widget.addItem(item)


    # 译图列表框添加图片
    def transImageWidgetAddImage(self, index) :

        item = QListWidgetItem(self.trans_image_widget)
        pixmap = self.createTransparentPixmap(180 * self.rate, 180 * self.rate)
        item.setText(index)
        item.setIcon(QIcon(pixmap))
        item.listWidget()
        self.trans_image_widget.addItem(item)


    # 创建透明Pixmap
    def createTransparentPixmap(self, width, height) :

        width, height = int(width), int(height)
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        img_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        pixmap = QPixmap()
        pixmap.loadFromData(base64.b64decode(img_base64))
        pixmap = pixmap.scaled(width, height, aspectRatioMode=Qt.KeepAspectRatio)

        return pixmap


    # 刷新编辑图列表框内item的图片
    def editImageWidgetRefreshImage(self, image_path) :

        if image_path not in self.image_path_list :
            return
        row = self.image_path_list.index(image_path)
        item = self.edit_image_widget.item(row)
        rdr_image_path = self.getRdrFilePath(image_path)
        pixmap = self.fromImageToPixmap(rdr_image_path)
        pixmap = pixmap.scaled(180*self.rate, 180*self.rate, aspectRatioMode=Qt.KeepAspectRatio)
        item.setIcon(QIcon(pixmap))


    # 刷新译图列表框内item的图片
    def transImageWidgetRefreshImage(self, image_path):

        if image_path not in self.image_path_list :
            return
        row = self.image_path_list.index(image_path)
        item = self.trans_image_widget.item(row)
        rdr_image_path = self.getRdrFilePath(image_path)
        pixmap = self.fromImageToPixmap(rdr_image_path)
        pixmap = pixmap.scaled(180*self.rate, 180*self.rate, aspectRatioMode=Qt.KeepAspectRatio)
        item.setIcon(QIcon(pixmap))


    # 展示原图图片大图
    def loadOriginalImage(self) :

        index = self.original_image_widget.currentRow()
        if index >= 0 and index < len(self.image_path_list) :
            image_path = self.image_path_list[index]
            self.renderImageAndTextBlock(image_path, "original")
            self.image_widget_index = index
            self.image_widget_scroll_bar_value = self.original_image_widget.verticalScrollBar().value()


    # 展示编辑图图片大图
    def loadEditImage(self) :

        index = self.edit_image_widget.currentRow()
        if index >= 0 and index < len(self.image_path_list):
            image_path = self.image_path_list[index]
            rdr_image_path = self.getRdrFilePath(image_path)
            if os.path.exists(rdr_image_path) :
                self.renderImageAndTextBlock(image_path, "edit")
            else :
                self.show_image_scroll_area.hide()
            self.image_widget_index = index
            self.image_widget_scroll_bar_value = self.edit_image_widget.verticalScrollBar().value()


    # 展示译图图片大图
    def loadTransImage(self):

        index = self.trans_image_widget.currentRow()
        if index >= 0 and index < len(self.image_path_list) :
            image_path = self.image_path_list[index]
            rdr_image_path = self.getRdrFilePath(image_path)
            if os.path.exists(rdr_image_path) :
                self.renderImageAndTextBlock(image_path, "trans")
            else :
                self.show_image_scroll_area.hide()
            self.image_widget_index = index
            self.image_widget_scroll_bar_value = self.trans_image_widget.verticalScrollBar().value()


    # 翻译进程
    def transProcess(self, image_path, execute_type="pass", use_sqlite=True) :
        """
        @execute_type
        all   : 所有步骤都执行
        pass  : 跳过已执行过的
        trans : 只执行翻译和文字渲染
        rdr   : 只执行文字渲染
        """
        # 漫画OCR
        start = time.time()
        if not os.path.exists(self.getJsonFilePath(image_path)) or execute_type == "all" :
            sign, ocr_result = self.mangaOCR(image_path)
            self.trans_process_bar.paintStatus("ocr", round(time.time()-start, 1), sign)
            # OCR失败
            if not sign :
                message = "OCR过程失败: %s"%ocr_result
                self.show_error_signal.emit([image_path, message])
                # OCR失败, 后续进度全部标记为失败
                self.trans_process_bar.paintStatus("trans", 0, False)
                self.trans_process_bar.paintStatus("ipt", 0, False)
                self.trans_process_bar.paintStatus("rdr", 0, False)
                return message
            # 没有文字的图
            if len(ocr_result.get("text_block", [])) == 0 :
                # 无文字的图OCR完成后后面均视为完成
                self.trans_process_bar.paintStatus("trans", 0, True)
                self.trans_process_bar.paintStatus("ipt", 0, True)
                self.trans_process_bar.paintStatus("rdr", 0, True)
                shutil.copy(image_path, self.getIptFilePath(image_path))
                shutil.copy(image_path, self.getRdrFilePath(image_path))
                # 直接将原图加入编辑图列表框
                self.editImageWidgetRefreshImage(image_path)
                # 直接将原图加入译图列表框
                self.transImageWidgetRefreshImage(image_path)
                return
        else :
            self.trans_process_bar.paintStatus("ocr", 0, True)

        # 翻译
        self.trans_result = ""
        def transThread() :
            start = time.time()
            trans_sign = False
            # 判断是否需要翻译
            if not os.path.exists(self.getJsonFilePath(image_path)) or execute_type == "all" or execute_type == "trans" :
                trans_sign = True
            else :
                with open(self.getJsonFilePath(image_path), "r", encoding="utf-8") as file :
                    json_data = json.load(file)
                if "translated_text" not in json_data:
                    trans_sign = True
            # 需要翻译
            if trans_sign :
                sign, trans_result = self.mangaTrans(image_path, use_sqlite)
                self.trans_process_bar.paintStatus("trans", round(time.time()-start, 1), sign)
                # 翻译失败
                if not sign :
                    #self.trans_process_bar.paintStatus("ipt", 0, False)
                    self.trans_process_bar.paintStatus("rdr", 0, False)
                    self.trans_result = "翻译过程失败: %s"%trans_result
            else :
                self.trans_process_bar.paintStatus("trans", 0, True)
        # 并发执行翻译
        trans_thread = utils.thread.createThread(transThread)

        # 文字消除
        start = time.time()
        if not os.path.exists(self.getIptFilePath(image_path)) or execute_type == "all" :
            sign, ipt_result = self.mangaTextInpaint(image_path)
            self.trans_process_bar.paintStatus("ipt", round(time.time()-start, 1), sign)
            # 文字消除失败
            if not sign :
                self.trans_process_bar.paintStatus("rdr", 0, False)
                message = "文字消除过程失败: %s"%ipt_result
                self.show_error_signal.emit([image_path, message])
                return message
        else:
            self.trans_process_bar.paintStatus("ipt", 0, True)

        # 阻塞, 等待翻译完成再执行文字渲染
        trans_thread.join()
        if self.trans_result :
            return self.trans_result

        # 漫画文字渲染
        start = time.time()
        if not os.path.exists(self.getRdrFilePath(image_path)) or execute_type == "all" or execute_type == "trans" or execute_type == "rdr" :
            sign, rdr_result = self.mangaTextRdr(image_path, execute_type)
            self.trans_process_bar.paintStatus("rdr", round(time.time()-start, 1), sign)
            if not sign :
                message = "文字渲染过程失败: %s"%rdr_result
                self.show_error_signal.emit([image_path, message])
                return message
            # 渲染好的图片加入编辑图列表框
            self.editImageWidgetRefreshImage(image_path)
            # 渲染好的图片加入译图列表框
            self.transImageWidgetRefreshImage(image_path)
        else:
            self.trans_process_bar.paintStatus("rdr", 0, True)

        # 刷新当前正在浏览的编辑图或译图
        if self.show_image_widget :
            if self.show_image_widget.original_image_path == image_path :
                if self.edit_image_widget.isVisible() :
                    self.flushed_render_image_and_text_block_signal.emit("edit")
                elif self.trans_image_widget.isVisible() :
                    self.flushed_render_image_and_text_block_signal.emit("trans")


    # 刷新当前正在浏览的编辑图或译图
    def transProcessFlushedRenderImageAndTextBlock(self, type) :

        self.renderImageAndTextBlock(self.show_image_widget.original_image_path, type)


    # 单图翻译
    def translaterItemWidget(self, item, item_type) :

        # 校验是否选择了翻译源
        if not self.object.config["mangaTrans"] :
            return utils.message.MessageBox("翻译失败", "请先选择要使用的翻译源     ", self.rate)
        # 获取图片路径
        if item_type == "edit" :
            row = self.edit_image_widget.indexFromItem(item).row()
        else :
            row = self.original_image_widget.indexFromItem(item).row()
        image_path = self.image_path_list[row]
        image_paths = []
        image_paths.append(image_path)
        # 进度条窗口
        self.trans_process_bar.modifyTitle("翻译中...请勿关闭此窗口")
        self.trans_process_bar.show()
        # 创建执行线程
        self.trans_all_button.setEnabled(False)
        thread = utils.thread.createMangaTransQThread(
            window=self,
            image_paths=image_paths,
            execute_type="all",
            use_sqlite=False
        )
        thread.signal.connect(self.finishTransProcessRefresh)
        thread.bar_signal.connect(self.trans_process_bar.paintProgressBar)
        thread.add_message_signal.connect(self.trans_process_bar.setMessageText)
        utils.thread.runQThread(thread)


    # 漫画OCR配置过滤
    def mangaOcrFilter(self, result, image_path="") :

        # 过滤错误的文本块
        new_text_block = []
        for index, val in enumerate(result.get("text_block", [])) :

            # 过滤<skip>
            new_texts = []
            new_coordinate = []
            skip_sign = False

            texts = val.get("texts", [])
            coordinate = val.get("coordinate", [])
            for text, coord in zip(texts, coordinate) :
                if not text or text == "<skip>":
                    skip_sign = True
                    continue
                new_texts.append(text)
                new_coordinate.append(coord)

            # 过滤空句子
            if not new_texts :
                continue

            # 过滤短句子
            if self.object.config["mangaFilterCharUse"] \
                    and len("".join(new_texts)) <= self.object.config["mangaFilterCharCount"] \
                    and image_path :
                # 如果过滤就将mask区域涂黑, 不消除该区域
                image = Image.open(self.getMaskFilePath(image_path))
                draw = ImageDraw.Draw(image)
                draw.rectangle((
                    val["block_coordinate"]["upper_left"][0],
                    val["block_coordinate"]["upper_left"][1],
                    val["block_coordinate"]["lower_right"][0],
                    val["block_coordinate"]["lower_right"][1]
                ), fill=0)
                image.save(self.getMaskFilePath(image_path))
                continue

            val["texts"] = new_texts
            val["coordinate"] = new_coordinate

            # 如果过滤过<skip>的情况就重新计算文本块的坐标
            if skip_sign :
                x_list, y_list = [], []
                for coordinate in val["coordinate"]:
                    for k in coordinate.keys():
                        x_list.append(coordinate[k][0])
                        y_list.append(coordinate[k][1])
                val["block_coordinate"]["upper_left"] = [min(x_list), min(y_list)]
                val["block_coordinate"]["upper_right"] = [max(x_list), min(y_list)]
                val["block_coordinate"]["lower_right"] = [max(x_list), max(y_list)]
                val["block_coordinate"]["lower_left"] = [min(x_list), max(y_list)]

            # 使用全局字体色
            if self.object.config["mangaFontColorUse"] and val.get("foreground_color", []):
                color = QColor(self.object.config["mangaFontColor"])
                f_r, f_g, f_b, f_a = color.getRgb()
                val["foreground_color"] = [f_r, f_g, f_b]
            # 使用全局轮廓色
            if self.object.config["mangaBgColorUse"] and val.get("background_color", []):
                color = QColor(self.object.config["mangaBgColor"])
                b_r, b_g, b_b, b_a = color.getRgb()
                val["background_color"] = [b_r, b_g, b_b]
            # 使用全局字体
            val["font_selector"] = self.object.config["mangaFontType"]
            # 使用全局轮廓宽度
            val["shadow_size"] = self.object.config["mangaShadowSize"]
            # 使用全局字体大小
            if self.object.config["mangaFontSizeUse"]:
                val["text_size"] = self.object.config.get("mangaFontSize", 36)

            new_text_block.append(val)

        # 过滤屏蔽词和替换词
        for index, val in enumerate(new_text_block):
            new_texts = []
            for text in val["texts"]:
                for filter in self.object.config["Filter"]:
                    if not filter[0]:
                        continue
                    text = text.replace(filter[0], filter[1])
                new_texts.append(text)
            new_text_block[index]["texts"] = new_texts

        result["text_block"] = new_text_block

        return result


    # 漫画OCR
    def mangaOCR(self, image_path) :

        filtrate = self.object.config.get("mangaFiltrateUse", True)
        sign, result = translator.ocr.dango.mangaOCR(
            object=self.object,
            filepath=image_path,
            image_base64=None,
            filtrate=filtrate,
            low_accuracy_mode=False,
            check_permission=self.check_permission
        )
        if sign :
            # 缓存mask图片
            with open(self.getMaskFilePath(image_path), "wb") as file :
                file.write(base64.b64decode(result["mask"]))
            del result["mask"]

            # 在线OCR配置过滤
            result = self.mangaOcrFilter(result, image_path)

            # 缓存ocr结果
            with open(self.getJsonFilePath(image_path), "w", encoding="utf-8") as file:
                json.dump(result, file, indent=4)

        return sign, result


    # 漫画文字消除
    def mangaTextInpaint(self, image_path) :

        # 从缓存文件里获取mask图片
        with open(self.getMaskFilePath(image_path), "rb") as file:
            mask = base64.b64encode(file.read()).decode("utf-8")
        # 请求漫画ipt
        sign, result = translator.ocr.dango.mangaIPT(self.object, image_path, mask, None, self.check_permission)
        if sign :
            # 缓存inpaint图片
            with open(self.getIptFilePath(image_path), "wb") as file :
                file.write(base64.b64decode(result["inpainted_image"]))

        return sign, result


    # 漫画翻译配置过滤
    def mangaTransFilter(self, json_data, delay_time, use_sqlite) :

        # 解析ocr结果获取原文
        original = []
        for val in json_data["text_block"] :
            tmp = ""
            for text in val["texts"] :
                tmp += text
            original.append(tmp)
        original = "\n".join(original)
        original = original.strip()

        translated_text = []
        result = ""
        sign = True

        # 空原文
        if not original :
            json_data["translated_text"] = translated_text
            return sign, json_data

        # 从数据库中获取翻译结果
        trans_map = {}
        if self.object.config["transHistoryUse"] :
            trans_map = utils.sqlite.selectTranslationDBBySrcAndTransType(original, self.logger)
            # 是否使用模糊匹配
            if not self.object.config["transHistoryPerfectUse"] and self.object.yaml["similar_score"] < 100 and not trans_map :
                similar_original = utils.sqlite.selectTransDataBySimilarity(original, self.object.yaml["similar_score"], self.logger)
                if similar_original :
                    trans_map = utils.sqlite.selectTranslationDBBySrcAndTransType(similar_original, self.logger)

        # 翻译源
        manga_trans = self.object.config["mangaTrans"]
        manga_trans = utils.sqlite.TRANS_MAP[manga_trans]

        # 如果本地有翻译缓存则直接使用
        if manga_trans in trans_map and use_sqlite :
            result = trans_map[manga_trans]
        else :
            # 调用翻译
            if manga_trans == "dango_private" :
                sign, result = translator.ocr.dango.dangoTrans(
                    object=self.object,
                    sentence=original,
                    language=self.object.config["mangaLanguage"]
                )

            elif manga_trans == "caiyun_private" :
                result = translator.api.caiyun(
                    sentence=original,
                    token=self.object.config["caiyunAPI"],
                    logger=self.logger
                )
                if re.match("^私人彩云[:：]", result) :
                    sign = False

            elif manga_trans == "tencent_private" :
                result = translator.api.tencent(
                    sentence=original,
                    secret_id=self.object.config["tencentAPI"]["Key"],
                    secret_key=self.object.config["tencentAPI"]["Secret"],
                    logger=self.logger
                )
                if re.match("^私人腾讯[:：]", result) :
                    sign = False

            elif manga_trans == "baidu_private" :
                result = translator.api.baidu(
                    sentence=original,
                    app_id=self.object.config["baiduAPI"]["Key"],
                    secret_key=self.object.config["baiduAPI"]["Secret"],
                    logger=self.logger
                )
                if re.match("^私人百度[:：]", result) :
                    sign = False

            elif manga_trans == "chatgpt_private" :
                result = translator.api.chatgpt(
                    object=self.object,
                    content=original,
                    delay_time=delay_time
                )
                if re.match("^私人ChatGPT[:：]", result) :
                    sign = False

            elif manga_trans == "aliyun_private" :
                sign, result = translator.api.aliyun(
                    access_key_id=self.object.config["aliyunAPI"]["Key"],
                    access_key_secret=self.object.config["aliyunAPI"]["Secret"],
                    source_language=self.object.config["mangaLanguage"],
                    text_to_translate=original,
                    logger=self.object.logger
                )

            elif manga_trans == "youdao_private" :
                sign, result = translator.api.youdao(
                    text=original,
                    app_key=self.object.config["youdaoAPI"]["Key"],
                    app_secret=self.object.config["youdaoAPI"]["Secret"],
                    logger=self.object.logger
                )

            elif manga_trans == "xiaoniu_private" :
                sign, result = translator.api.xiaoniu(
                    apikey=self.object.config["xiaoniuAPI"],
                    sentence=original,
                    language=self.object.config["mangaLanguage"],
                    logger=self.logger
                )

            elif manga_trans == "huoshan_private" :
                sign, result = translator.api.huoshan(
                    ak=self.object.config["huoshanAPI"]["Key"],
                    sk=self.object.config["huoshanAPI"]["Secret"],
                    text=original,
                    logger=self.logger
                )

        # 翻译成功
        if sign :
            # 翻译结果缓存到本地数据库
            if manga_trans not in trans_map :
                utils.sqlite.insertTranslationDB(self.logger, original, manga_trans, result)
            # 根据屏蔽词过滤
            for filter in self.object.config["Filter"] :
                if not filter[0] :
                    continue
                result = result.replace(filter[0], filter[1])
            # 按照text_block长度分割翻译结果
            for text in result.split("\n") :
                translated_text.append(text)
            translated_text = translated_text[:len(json_data["text_block"])]
            json_data["translated_text"] = translated_text
        else :
            # 翻译失败, result为错误信息
            json_data = result

        return sign, json_data


    # 图片翻译
    def mangaTrans(self, image_path, use_sqlite) :

        # 从缓存文件中获取json结果
        with open(self.getJsonFilePath(image_path), "r", encoding="utf-8") as file:
            json_data = json.load(file)

        # chatgpt延时
        delay_time = 0
        if self.object.config["mangaChatgptDelayUse"] == True :
            delay_time = self.object.config["mangaChatgptDelayTime"]
        # 漫画翻译配置过滤
        sign, result = self.mangaTransFilter(json_data, delay_time, use_sqlite)
        if not sign :
            return sign, result

        # 缓存翻译结果
        with open(self.getJsonFilePath(image_path), "w", encoding="utf-8") as file :
            json.dump(result, file, indent=4)

        return True, result


    # 漫画文字渲染
    def mangaTextRdr(self, image_path, execute_type) :

        # 从缓存文件中获取json结果
        with open(self.getJsonFilePath(image_path), "r", encoding="utf-8") as file :
            json_data = json.load(file)

        new_text_blocks = []
        if execute_type == "trans" or execute_type == "rdr" :
            for text_block in json_data["text_block"] :
                # 修改字体颜色
                if self.object.config["mangaFontColorUse"] :
                    color = QColor(self.object.config["mangaFontColor"])
                    f_r, f_g, f_b, f_a = color.getRgb()
                    text_block["foreground_color"] = [f_r, f_g, f_b]
                # 修改轮廓颜色
                if self.object.config["mangaBgColorUse"] :
                    color = QColor(self.object.config["mangaBgColor"])
                    b_r, b_g, b_b, b_a = color.getRgb()
                    text_block["background_color"] = [b_r, b_g, b_b]
                # 字体大小
                if self.object.config["mangaFontSizeUse"] :
                    text_block["text_size"] = self.object.config["mangaFontSize"]
                # 轮廓宽度
                text_block["shadow_size"] = self.object.config["mangaShadowSize"]
                # 使用全局字体
                text_block["font_selector"] = self.object.config["mangaFontType"]

                new_text_blocks.append(text_block)
        else :
            new_text_blocks = json_data["text_block"]

        # 从缓存文件里获取ipt图片
        with open(self.getIptFilePath(image_path), "rb") as file :
            ipt = base64.b64encode(file.read()).decode("utf-8")
        # 漫画rdr
        sign, result = translator.ocr.dango.mangaRDR(
            object=self.object,
            trans_list=json_data["translated_text"],
            inpainted_image=ipt,
            text_block=new_text_blocks,
            font=self.object.config["mangaFontType"],
            check_permission=self.check_permission
        )
        if sign :
            # 缓存ipt图片
            with open(self.getRdrFilePath(image_path), "wb") as file :
                file.write(base64.b64decode(result["rendered_image"]))
            # 缓存ocr结果
            if execute_type == "trans" or execute_type == "rdr" :
                json_data["text_block"] = new_text_blocks
                with open(self.getJsonFilePath(image_path), "w", encoding="utf-8") as file :
                    json.dump(json_data, file, indent=4)

        return sign, result


    # 获取工作目录
    def getDangoMangaPath(self, image_path) :

        # 获取图片翻译缓存目录
        base_path = os.path.dirname(image_path)
        dango_manga_path = os.path.join(base_path, "dango_manga")
        # 如果目录不存在就创建工作缓存目录
        if not os.path.exists(dango_manga_path) :
            os.mkdir(dango_manga_path)
        # 如果目录不存在就创建工作缓存目录
        tmp_path = os.path.join(dango_manga_path, "tmp")
        if not os.path.exists(tmp_path) :
            os.mkdir(tmp_path)
        # 获取不带拓展名的文件名
        file_name = os.path.splitext(os.path.basename(image_path))[0]

        return dango_manga_path, file_name


    # 获取某张图对应的Json结果文件缓存路径
    def getJsonFilePath(self, image_path) :

        dango_manga_path, file_name = self.getDangoMangaPath(image_path)
        tmp_path = os.path.join(dango_manga_path, "tmp")
        file_path = os.path.join(tmp_path, "{}.json".format(file_name))

        return file_path


    # 获取某张图对应的mask结果文件缓存路径
    def getMaskFilePath(self, image_path) :

        dango_manga_path, file_name = self.getDangoMangaPath(image_path)
        tmp_path = os.path.join(dango_manga_path, "tmp")
        file_path = os.path.join(tmp_path, "{}_mask.png".format(file_name))

        return file_path


    # 获取某张图对应的文字消除结果文件缓存路径
    def getIptFilePath(self, image_path) :

        dango_manga_path, file_name = self.getDangoMangaPath(image_path)
        tmp_path = os.path.join(dango_manga_path, "tmp")
        file_path = os.path.join(tmp_path, "{}_ipt.png".format(file_name))

        return file_path


    # 获取某张图对应的文字渲染结果文件缓存路径
    def getRdrFilePath(self, image_path) :

        dango_manga_path, file_name = self.getDangoMangaPath(image_path)
        file_path = os.path.join(dango_manga_path, "{}.png".format(file_name))

        return file_path


    # 渲染图片和文本块
    def renderImageAndTextBlock(self, image_path, show_type) :

        original_image_path = image_path
        ipt_image_path = self.getIptFilePath(image_path)
        if show_type == "original" :
            json_data = None
        elif show_type == "edit" :
            with open(self.getJsonFilePath(image_path), "r", encoding="utf-8") as file:
                json_data = json.load(file)
            image_path = self.getRdrFilePath(image_path)
        elif show_type == "trans" :
            image_path = self.getRdrFilePath(image_path)
            json_data = None
        else :
            return

        # 切换图片的时候保持比例
        init_image_rate = []
        if self.show_image_widget :
            init_image_rate = copy.deepcopy(self.show_image_widget.image_rate)

        w_rate = self.width() / self.window_width
        h_rate = self.height() / self.window_height
        self.show_image_scroll_area.setWidget(None)
        self.show_image_widget = RenderTextBlock(
            rate=(w_rate, h_rate),
            image_path=image_path,
            original_image_path=original_image_path,
            ipt_image_path=ipt_image_path,
            json_data=json_data,
            edit_window=self.trans_edit_ui
        )
        self.show_image_scroll_area.setWidget(self.show_image_widget)
        self.show_image_scroll_area.show()

        # 切换图片的时候保持比例
        if init_image_rate :
            self.setImageInitRate(init_image_rate)
        # 刷新状态栏
        self.refreshStatusLabel(image_path)


    # 设置图片初始缩放比例
    def setImageInitRate(self, init_image_rate) :

        self.show_image_widget.image_rate = init_image_rate
        pixmap = self.show_image_widget.image_pixmap.scaled(
            self.show_image_widget.image_pixmap.width() * self.show_image_widget.image_rate[0],
            self.show_image_widget.image_pixmap.height() * self.show_image_widget.image_rate[1]
        )
        self.show_image_widget.image_label.setPixmap(pixmap)
        self.show_image_widget.rate_label.setText("{}%".format(round(self.show_image_widget.image_rate[0] * 100)))
        self.show_image_widget.matchButtonSize()


    # 翻译完成后刷新译图栏
    def finishTransProcessRefresh(self, value, signal) :

        if not signal :
            if value:
                # @TODO 缺少错误处理
                pass
            self.trans_process_bar.modifyTitle("翻译完成")
            self.trans_all_button.setEnabled(True)


    # 一键翻译
    def clickTransAllButton(self, execute_type) :

        if len(self.image_path_list) == 0 :
            return utils.message.MessageBox("翻译失败", "请先导入要翻译的图片      ")

        self.trans_all_button.setEnabled(False)
        # 进度条窗口
        self.trans_process_bar.modifyTitle("翻译中...请勿关闭此窗口")
        self.trans_process_bar.show()
        # 创建执行线程
        thread = utils.thread.createMangaTransQThread(
            window=self,
            image_paths=self.image_path_list,
            execute_type=execute_type,
            use_sqlite=True
        )
        thread.signal.connect(self.finishTransProcessRefresh)
        thread.bar_signal.connect(self.trans_process_bar.paintProgressBar)
        thread.add_message_signal.connect(self.trans_process_bar.setMessageText)
        utils.thread.runQThread(thread)


    # 打开使用教程
    def openUseTutorial(self) :

        url = self.object.yaml["dict_info"]["manga_tutorial"]
        try:
            webbrowser.open(url, new=0, autoraise=True)
        except Exception:
            self.logger.error(format_exc())
            utils.message.MessageBox("打开失败",
                                     "请尝试手动打开此地址:\n%s     "%url)


    # 窗口尺寸变化信号
    def resizeEvent(self, event) :

        w = event.size().width()
        h = event.size().height()
        w_rate = w / self.window_width
        h_rate = h / self.window_height

        # 设置字体
        self.setStyleSheet("font: %spt '%s';"%(self.font_size*w_rate, self.font_type))
        # 导入原图按钮
        self.customSetGeometry(self.input_image_button, 0, 0, 120, 35, w_rate, h_rate)
        # 底部状态栏
        self.status_label.setGeometry(
            0, h - 30 * h_rate,
            w, 30 * h_rate
        )
        # 顶部工具栏底色Label
        self.top_background_label.setGeometry(0, 0, w, self.input_image_button.height())
        # 一键翻译按钮
        self.trans_all_button.setGeometry(
            self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 译图导出按钮
        self.output_image_button.setGeometry(
            self.trans_all_button.x() + self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 选择语种
        self.select_language_button.setGeometry(
            self.output_image_button.x() + self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 选择翻译源按钮
        self.select_trans_button.setGeometry(
            self.select_language_button.x() + self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 高级设置按钮
        self.setting_button.setGeometry(
            self.select_trans_button.x() + self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 教程按钮
        self.tutorial_button.setGeometry(
            w-self.input_image_button.width(), 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 购买按钮
        self.buy_button.setGeometry(
            w-self.input_image_button.width()*2, 0,
            self.input_image_button.width(), self.input_image_button.height()
        )
        # 工具栏横向分割线
        self.cut_line_label1.setGeometry(
            0, self.input_image_button.height(),
            w, 1
        )
        # 列表框按钮底色Label
        self.widget_button_background_label.setGeometry(
            0, self.input_image_button.height(),
            200 * w_rate, 25 * h_rate
        )
        # 图片列表框原图按钮
        self.original_image_button.setGeometry(
            0, self.input_image_button.height(),
            66 * w_rate, 25 * h_rate
        )
        # 原图按钮 和 编辑按钮 竖向分割线
        self.cut_line_label2.setGeometry(
            self.original_image_button.width() + 1, self.input_image_button.height(),
            1, self.original_image_button.height()
        )
        # 图片列表框编辑按钮
        self.edit_image_button.setGeometry(
            self.cut_line_label2.x(), self.input_image_button.height(),
            self.original_image_button.width(), self.original_image_button.height()
        )
        # 编辑按钮 和 译图按钮 竖向分割线
        self.cut_line_label3.setGeometry(
            self.edit_image_button.x() + self.edit_image_button.width() + 1, self.input_image_button.height(),
            1, self.original_image_button.height()
        )
        # 图片列表框译图按钮
        self.trans_image_button.setGeometry(
            self.cut_line_label3.x(), self.input_image_button.height(),
            self.original_image_button.width(), self.original_image_button.height()
        )
        # 译图右侧竖向分割线
        self.cut_line_label4.setGeometry(
            self.trans_image_button.x() + self.trans_image_button.width(), self.input_image_button.height(),
            1, self.original_image_button.height()
        )
        # 原图列表框
        self.original_image_widget.setGeometry(
            0, self.input_image_button.height() + self.original_image_button.height(),
            self.cut_line_label4.x(), self.status_label.y() - (self.input_image_button.height()+self.original_image_button.height()*2)
        )
        # 编辑列表框
        self.edit_image_widget.setGeometry(
            0, self.input_image_button.height() + self.original_image_button.height(),
            self.cut_line_label4.x(), self.original_image_widget.height()
        )
        # 译图列表框
        self.trans_image_widget.setGeometry(
            0, self.input_image_button.height() + self.original_image_button.height(),
            self.cut_line_label4.x(), self.original_image_widget.height()
        )
        # 批量删除按钮
        self.delete_button.setGeometry(
            0, self.status_label.y() - self.original_image_button.height(),
            self.cut_line_label4.x()//2, self.original_image_button.height()
        )
        # 全部删除按钮
        self.all_delete_button.setGeometry(
            self.delete_button.width(), self.delete_button.y(),
            self.cut_line_label4.x()//2, self.original_image_button.height()
        )
        # 批量删除按钮上方横向分割线
        self.cut_line_label5.setGeometry(
            0, self.delete_button.y()-1,
            self.cut_line_label4.x(), 1
        )
        # 图片大图展示
        if self.hide_image_widget_status :
            self.show_image_scroll_area.setGeometry(
                0, self.input_image_button.height(),
                w, self.status_label.y()-self.input_image_button.height()
            )
        else :
            self.show_image_scroll_area.setGeometry(
                self.cut_line_label4.x(), self.input_image_button.height(),
                w-self.cut_line_label4.x(), self.status_label.y()-self.input_image_button.height()
            )
        # 错误展示提示窗
        self.show_error_label.setGeometry(
            self.show_image_scroll_area.x(), self.show_image_scroll_area.y(),
            self.show_image_scroll_area.width(), self.show_image_scroll_area.height() / 8
        )
        self.show_error_label.setStyleSheet("background-color: #98ff98;"
                                            "font: %spt '%s';"%((self.font_size+5*w_rate), self.font_type))
        # 隐藏图片列表框按钮
        if self.hide_image_widget_status :
            self.hide_image_widget_button.setGeometry(
                0, self.show_image_scroll_area.y(),
                15 * w_rate, self.show_image_scroll_area.height()
            )
        else :
            self.hide_image_widget_button.setGeometry(
                self.cut_line_label4.x(), self.show_image_scroll_area.y(),
                15*w_rate, self.show_image_scroll_area.height()
            )
        # 上一页按钮
        if self.hide_image_widget_status :
            self.last_page_button.setGeometry(
                20*w_rate, (self.show_image_scroll_area.height()-300*h_rate) // 2,
                50*w_rate, 300*h_rate
            )
        else :
            self.last_page_button.setGeometry(
                self.cut_line_label4.x()+20*w_rate, (self.show_image_scroll_area.height()-300*h_rate) // 2,
                50*w_rate, 300*h_rate
            )
        # 下一页按钮
        self.next_page_button.setGeometry(
            w-self.last_page_button.width()-20*w_rate, self.last_page_button.y(),
            self.last_page_button.width(), self.last_page_button.height()
        )
        # 图片大图展示
        if self.show_image_widget :
            self.show_image_widget.resize(self.show_image_scroll_area.width(), self.show_image_scroll_area.height())
        # 图片大图展示背景
        try :
            self.background_label.setPixmap(
                ui.static.icon.MANGA_PIXMAP.scaled(
                    self.show_image_scroll_area.width()*0.7,
                    self.show_image_scroll_area.height()*0.7,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation)
            )
            self.show_image_scroll_area.setWidget(self.background_label)
        except Exception :
            pass


    # 展示错误消息
    def showError(self, messages: list) :

        # 刷新提示消息
        text = ""
        for message in messages :
            if message == messages[-1] :
                text += "   " + message
            else :
                text += "   " + message + "\n"
        self.show_error_label.setText(text)
        self.show_error_label.show()

        # 刷新停留时间
        self.show_error_start_time = time.time()
        if self.show_error_sign :
            return

        # 展示消息等待线程, 停留时间5s
        def waitThread() :
            self.show_error_sign = True
            while True :
                if time.time() - self.show_error_start_time >= 5 :
                    self.show_error_sign = False
                    return self.show_error_label.hide()
        utils.thread.createThread(waitThread)


    # 拖拽文件信号
    def dragEnterEvent(self, event) :
        try :
            if event.mimeData().hasUrls():
                event.accept()
            else:
                event.ignore()
        except Exception :
            self.logger.error(traceback.format_exc())


    # 拖拽导入文件
    def dropEvent(self, event) :

        try :
            image_list = []
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                # 过滤非图片文件
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext != ".png" and file_ext != ".jpg" and file_ext != ".jpeg" and file_ext != ".webp" :
                    continue
                image_list.append(file_path)
            # 去重
            image_list = list(set(image_list))

            if image_list :
                event.accept()
                # 清除所有图片
                #self.clearAllImages()
                # 根据文件名排序
                image_list = self.dirFilesPathSort(image_list)
                # 进度条窗口
                self.input_images_progress_bar.modifyTitle("导入图片 -- 加载中请勿关闭此窗口")
                self.input_images_progress_bar.show()
                # 导入图片线程
                thread = utils.thread.createInputImagesQThread(self, image_list)
                thread.bar_signal.connect(self.input_images_progress_bar.paintProgressBar)
                thread.image_widget_signal.connect(self.inputImage)
                utils.thread.runQThread(thread)

        except Exception :
            self.logger.error(traceback.format_exc())


    # 校验图片翻译接口权限
    def checkPermission(self) :

        # 校验团子token是否存在
        token = self.object.config.get("DangoToken", "")
        if not token :
            # 登录OCR服务获取token
            utils.http.loginDangoOCR(self.object)
            token = self.object.config.get("DangoToken", "")
        if not token :
            return

        url = self.object.yaml["dict_info"].get("dango_check_permission", "https://capiv1.ap-sh.starivercs.cn/OCR/Admin/CheckPermission")
        url += "?Token={}".format(token)
        body = {"Type": 1}

        while True :
            # 是否处于漫画翻译界面, 只有打开该界面才进行试用检测
            if not self.is_check_permission_sign :
                break
            # 请求查询使用权限接口
            resp = utils.http.post(url=url, body=body, logger=self.logger, headers=None, timeout=5)
            if not resp :
                time.sleep(5)
                continue
            code = resp.get("Code", -1)
            # 有使用权限
            if code == 0 :
                self.check_permission = False
                break
            # 无使用权限
            elif code == -900 :
                if len(self.image_path_list) == 0 :
                    self.show_error_label.setText("   图片翻译服务为付费功能, 可以购买后再使用, 购买按钮在界面右上角\n"
                                                  "   当前已自动打开试用, 可以直接试用看看效果, 试用次数详见底部状态栏\n"
                                                  "   如您已购买但仍处于试用状态, 请直接通过交流群联系任何管理和客服")
                    self.show_error_label.show()
                    self.check_permission = True
                else :
                    self.show_error_label.hide()
                    continue
            else :
                continue

            # 试用次数
            self.mangaReadCount()
            # 刷新底部状态栏
            self.refreshStatusLabel()
            # 延时
            time.sleep(5)


        # 查询有效时间
        sign, valid_time = utils.http.mangaOCRQueryQuota(self.object)
        if sign :
            self.valid_time = valid_time
        self.mangaReadCount()
        self.refreshStatusLabel()
        self.show_error_label.hide()


    # 查询图片翻译接口试用次数
    def mangaReadCount(self) :

        url = self.object.yaml["dict_info"].get("manga_read_count", "https://dl.ap-sh.starivercs.cn/v2/probate/manga_read_count")
        body = {"Username": self.object.yaml["user"]}
        resp = utils.http.post(url=url, body=body, logger=self.logger, headers=None, timeout=5)
        if not resp :
            self.manga_read_count = -1
            return
        if resp.get("Code", -1) != 0 :
            self.manga_read_count = -1
            return
        self.manga_read_count = resp.get("Data", -1)


    # 左右切换图片列表框
    def switchImageWidget(self, sign) :

        if self.click_button_type == "original" and sign == "right" :
            self.clickImageButton("edit")
            return
        if self.click_button_type == "edit" :
            if sign == "left" :
                self.clickImageButton("original")
            elif sign == "right" :
                self.clickImageButton("trans")
            return
        if self.click_button_type == "trans" and sign == "left" :
            self.clickImageButton("edit")
            return


    # 判断文件大小(MB)
    def getFileSize(self, file_path) :

        size_in_bytes = os.path.getsize(file_path)
        size_in_mb = size_in_bytes / (1024 * 1024)
        return size_in_mb


    # 调整图片大小
    def adjustImageSize(self, image_path, target_size):

        try :
            ext = pathlib.Path(image_path).suffix.replace(".", "")
            format = self.image_ext_map[ext]

            # 打开原始图片
            image = Image.open(image_path)
            image_data = io.BytesIO()
            image.save(image_data, format=format, quality=95)
            factor = 0.9
            # 调整图片尺寸
            while image_data.tell() > target_size :
                image_data.seek(0)
                image_data.truncate()
                image = image.resize((int(image.width * factor), int(image.height * factor)))
                image.save(image_data, format=format, quality=95)
                factor -= 0.1
                if factor < 0.1 :
                    break
            # 保存调整后的图片
            image_data.seek(0)
            adjusted_image = Image.open(image_data)
            adjusted_image.save(image_path, format, quality=95)
        except Exception :
            self.logger.error(traceback.format_exc())


    # 修复坏图
    def repairBadImage(self, image_path) :

        try :
            image = Image.open(image_path)
            image.load()
        except Exception :
            ImageFile.LOAD_TRUNCATED_IMAGES = True
            image.save(image_path, quality=95)
            ImageFile.LOAD_TRUNCATED_IMAGES = False


    # 读取图片加载到QPixmap
    def fromImageToPixmap(self, image_path) :

        for _ in range(3) :
            image = QImage(image_path)
            if image.width() != 0 and image.height() != 0 :
                break
        if image.width() == 0 and image.height() == 0 :
            try :
                image_data = Image.open(image_path).convert("RGBA").tobytes()
                image = QImage(image_data, image.size[0], image.size[1], QImage.Format_RGBA8888)
            except Exception :
                self.logger.error(traceback.format_exc())

        pixmap = QPixmap.fromImage(image)

        return pixmap


    # 窗口显示信号
    def showEvent(self, e) :

        self.is_check_permission_sign = True
        utils.thread.createThread(self.checkPermission)


    # 窗口关闭处理
    def closeEvent(self, event) :

        self.is_check_permission_sign = False
        self.hide()
        self.object.translation_ui.show()
        if self.object.range_ui.show_sign == True :
            self.object.range_ui.show()


# 渲染文本块
class RenderTextBlock(QWidget) :

    def __init__(self, rate, image_path, original_image_path,
                 ipt_image_path, json_data, edit_window) :

        super(RenderTextBlock, self).__init__()
        self.rate = rate
        self.image_path = image_path
        self.original_image_path = original_image_path
        self.ipt_image_path = ipt_image_path
        self.json_data = json_data
        self.trans_edit_ui = edit_window
        self.object = edit_window.object
        self.logger = self.object.logger
        self.image_rate = [1, 1]
        self.button_list = []
        self.paint_status = False
        self.paint_button = None
        self.ui()


    def ui(self) :

        # 窗口大小
        self.resize(1000*self.rate[0], 635*self.rate[1])
        # 窗口无标题栏、窗口置顶、窗口透明
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        # 样式
        self.setCursor(ui.static.icon.PIXMAP_CURSOR)
        self.setStyleSheet("QMenu {color: #5B8FF9; background-color: #FFFFFF;}"
                           "QMenu::item:selected:enabled {background: #E5F5FF;}"
                           "QMenu::item:checked {background: #E5F5FF;}")

        # 图片大图展示
        self.scroll_area = CustomScrollArea(self)
        self.scroll_area.setGeometry(0, 0, self.width(), self.height())
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.scroll_area.setCursor(Qt.OpenHandCursor)

        self.image_label = CustomPaintLabel(self)
        self.image_label.setCursor(Qt.OpenHandCursor)
        self.image_label.paint_sign.connect(self.paintTextBlockButton)
        self.image_label.paint_reset_sign.connect(self.paintTextBlockButtonReset)
        self.image_label.paint_recover_sign.connect(self.paintAreaRecoverReset)
        widget = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        widget.setLayout(layout)
        self.scroll_area.setWidget(widget)

        # 手动OCR按钮
        self.manual_ocr_button = QPushButton(self)
        self.manual_ocr_button.setText(" 手动绘制")
        self.manual_ocr_button.setIcon(ui.static.icon.TEXT_BLOCK_ICON)
        self.manual_ocr_button.setToolTip("<b>手动绘制文字识别框, 点击后可通过长按鼠标左键在编辑图上拉取新的识别框, 再次点击按钮释放</b>")
        self.manual_ocr_button.setGeometry(0, 590*self.rate[1], 100*self.rate[0], 30*self.rate[1])
        self.manual_ocr_button.setStyleSheet("QPushButton {color: #5B8FF9;}"
                                             "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                             "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.manual_ocr_button.clicked.connect(self.manualOCR)
        if not self.json_data :
            self.manual_ocr_button.hide()

        # 区域还原按钮
        self.area_recover_button = QPushButton(self)
        self.area_recover_button.setText(" 区域还原")
        self.area_recover_button.setIcon(ui.static.icon.RECOVER_ICON)
        self.area_recover_button.setToolTip("<b>通过在编辑图上长按鼠标左键, 框出一个区域, 该区域会恢复原图的摸样</b>")
        self.area_recover_button.setGeometry(100*self.rate[0], 590*self.rate[1], 100*self.rate[0], 30*self.rate[1])
        self.area_recover_button.setStyleSheet("QPushButton {color: #5B8FF9;}"
                                               "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                               "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
        self.area_recover_button.clicked.connect(self.areaRecover)
        if not self.json_data :
            self.area_recover_button.hide()

        # 显示图片缩放比例
        self.rate_label = TransparentButton(self)
        self.rate_label.setIcon(ui.static.icon.MAGNIFYING_GLASS_ICON)
        self.rate_label.setGeometry(930*self.rate[0], 590*self.rate[1], 60*self.rate[0], 30*self.rate[1])
        # 载入大图
        self.loadImage()

        if not self.json_data or not self.json_data.get("text_block", []) or not self.json_data.get("translated_text", []) :
            return

        # 渲染文本框
        index = 0
        for i, text_block in enumerate(self.json_data["text_block"]) :
            trans_text = ""
            if i < len(self.json_data["translated_text"]) :
                trans_text = self.json_data["translated_text"][i]
            # 计算文本坐标
            x_0 = text_block["block_coordinate"]["upper_left"][0]
            y_0 = text_block["block_coordinate"]["upper_left"][1]
            w_0 = text_block["block_coordinate"]["lower_right"][0] - x_0
            h_0 = text_block["block_coordinate"]["lower_right"][1] - y_0
            # 计算缩放比例
            x = x_0*self.image_rate[0]
            y = y_0*self.image_rate[1]
            w = w_0*self.image_rate[0]
            h = h_0*self.image_rate[1]
            # 绘制矩形框
            button = CustomTextBlockButton(self.image_label)
            button.setCursor(ui.static.icon.EDIT_CURSOR)
            button.initConfig(
                text_block=text_block,
                trans=trans_text,
                rect=(x_0, y_0, w_0, h_0),
                index=index,
                original_image_path=self.original_image_path,
                ipt_image_path=self.ipt_image_path,
                rdr_image_path=self.image_path,
                font_type=text_block.get("font_selector", "Noto_Sans_SC/NotoSansSC-Regular"),
                shadow_size=text_block.get("shadow_size", 4),
                text_size=text_block.get("text_size", 36)
            )
            # 打开文本框编辑信号
            button.click_signal.connect(self.clickTextBlock)
            # 移动文本框信号
            button.move_signal.connect(self.refreshTextBlockPosition)
            button.setGeometry(x, y, w, h)
            button.setStyleSheet("QPushButton {background: transparent; border: 2px solid red;}"
                                 "QPushButton:hover {background-color: rgba(62, 62, 62, 0.1);}")
            # 文本框右键菜单
            button.setContextMenuPolicy(Qt.CustomContextMenu)
            button.customContextMenuRequested.connect(lambda _, b=button: self.showTextBlockButtonMenu(b))
            index += 1
            self.button_list.append(button)


    # 绘制矩形框按钮信号槽
    def paintTextBlockButton(self, x, y, w, h) :

        # 初始化框按钮
        if not self.paint_button :
            self.paint_button = CustomTextBlockButton(self.image_label)
            self.paint_button.setCursor(ui.static.icon.EDIT_CURSOR)
            self.paint_button.setStyleSheet("QPushButton {background: transparent; border: 2px solid red;}"
                                            "QPushButton:hover {background-color: rgba(62, 62, 62, 0.1)}")
            self.paint_button.setGeometry(x, y, w, h)
            self.paint_button.show()

            # 如果是绘制OCR框状态
            if self.image_label.paint_type == "ocr" :
                # 打开文本框编辑信号
                self.paint_button.click_signal.connect(self.clickTextBlock)
                # 移动文本框信号
                self.paint_button.move_signal.connect(self.refreshTextBlockPosition)
                # 文本框右键菜单
                self.paint_button.setContextMenuPolicy(Qt.CustomContextMenu)
                self.paint_button.customContextMenuRequested.connect(lambda _, b=self.paint_button: self.showTextBlockButtonMenu(b))

        self.paint_button.setGeometry(x, y, w, h)


    # 结束绘制矩形框按钮信号槽
    def paintTextBlockButtonReset(self, sign) :

        try :
            if not self.paint_button :
                if self.paint_status :
                    self.manualOCR()
                return
            # 如果框太小就直接删掉, 防止误操作绘制出错误的框
            if self.paint_button.width() <= 10 and self.paint_button.height() <= 10 :
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return

            # 计算坐标
            x = int(self.paint_button.x() / self.image_rate[0])
            y = int(self.paint_button.y() / self.image_rate[1])
            w = int(self.paint_button.width() / self.image_rate[0])
            h = int(self.paint_button.height() / self.image_rate[1])
            # 打开原图, 按照坐标截图
            original_image = Image.open(self.original_image_path)
            original_cut_image = original_image.crop((x, y, x+w, y+h))
            # 截图转换为base64
            buffered = io.BytesIO()
            original_cut_image.save(buffered, format="PNG")
            original_cut_image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # 请求OCR
            sign, ocr_result = translator.ocr.dango.mangaOCR(
                object=self.object,
                filepath=None,
                image_base64=original_cut_image_base64,
                filtrate=False,
                low_accuracy_mode=True,
                check_permission=self.object.manga_ui.check_permission
            )
            if not sign :
                utils.message.MessageBox("文字识别失败", ocr_result, self.rate)
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return
            if len(ocr_result["text_block"]) != 1 :
                utils.message.MessageBox("手动识别失败", "无效的文本区域", self.rate)
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return
            # OCR配置过滤
            ocr_result = self.object.manga_ui.mangaOcrFilter(ocr_result)

            # 请求ipt
            self.ipt_sign = True
            self.ipt_result = ""
            def iptThread() :
                self.ipt_sign, self.ipt_result = translator.ocr.dango.mangaIPT(
                    object=self.object,
                    filepath=None,
                    mask=ocr_result["mask"],
                    image_base64=original_cut_image_base64,
                    check_permission=self.object.manga_ui.check_permission
                )
            # 并发执行文字消除
            ipt_thread = utils.thread.createThread(iptThread)

            # 请求翻译
            sign, trans_result = self.object.manga_ui.mangaTransFilter(ocr_result, 0, True)
            if not sign :
                utils.message.MessageBox("翻译失败", trans_result, self.rate)
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return
            ocr_result = trans_result

            # 阻塞, 等待ipt执行完毕
            ipt_thread.join()
            ipt_result = self.ipt_result
            if not self.ipt_sign :
                utils.message.MessageBox("文字消除失败", ipt_result, self.rate)
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return

            # 请求rdr
            sign, rdr_result = translator.ocr.dango.mangaRDR(
                object=self.object,
                trans_list=ocr_result["translated_text"],
                inpainted_image=ipt_result["inpainted_image"],
                text_block=ocr_result["text_block"],
                font=self.object.config["mangaFontType"],
                check_permission=self.object.manga_ui.check_permission
            )
            if not sign :
                utils.message.MessageBox("文字渲染失败", rdr_result, self.rate)
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.manualOCR()
                return

            # 重新计算 block_coordinate
            for k, v in ocr_result["text_block"][0]["block_coordinate"].items() :
                v[0] += x
                v[1] += y
                ocr_result["text_block"][0]["block_coordinate"][k] = v
            # 重新计算 coordinate
            for i, coordinate in enumerate(ocr_result["text_block"][0]["coordinate"]) :
                for k, v in coordinate.items() :
                    v[0] += x
                    v[1] += y
                    ocr_result["text_block"][0]["coordinate"][i][k] = v

            # 全部都成功, 刷新新的文本框按钮信息
            del ocr_result["mask"]
            self.paint_button.initConfig(
                text_block=ocr_result["text_block"][0],
                trans=ocr_result["translated_text"][0],
                rect=(x, y, w, h),
                index=len(self.button_list),
                original_image_path=self.original_image_path,
                ipt_image_path=self.ipt_image_path,
                rdr_image_path=self.image_path,
                font_type=ocr_result["text_block"][0].get("font_selector", "Noto_Sans_SC/NotoSansSC-Regular"),
                shadow_size=ocr_result["text_block"][0].get("shadow_size", 4),
                text_size=ocr_result["text_block"][0].get("text_size", 36)
            )
            self.button_list.append(self.paint_button)

            # 渲染后的新图贴在大图上
            rdr_cut_image = Image.open(io.BytesIO(base64.b64decode(rdr_result["rendered_image"])))
            rdr_image = Image.open(self.image_path)
            rdr_image.paste(rdr_cut_image, (x, y))
            rdr_image.save(self.image_path)
            # ipt后的截图贴回ipt图上
            ipt_cut_image = Image.open(io.BytesIO(base64.b64decode(ipt_result["inpainted_image"])))
            ipt_image = Image.open(self.ipt_image_path)
            ipt_image.paste(ipt_cut_image, (x, y))
            ipt_image.save(self.ipt_image_path)

            # 刷新缓存文件中获取json结果
            file_name = os.path.splitext(os.path.basename(self.original_image_path))[0]
            json_file_path = os.path.join(os.path.dirname(self.ipt_image_path), "%s.json"%file_name)
            with open(json_file_path, "r", encoding="utf-8") as file :
                json_data = json.load(file)
            if "translated_text" not in json_data :
                json_data["translated_text"] = []
            json_data["translated_text"].append(self.paint_button.trans)
            if "text_block" not in json_data :
                json_data["translated_text"] = []
            json_data["text_block"].append(self.paint_button.text_block)
            # 缓存ocr结果
            with open(json_file_path, "w", encoding="utf-8") as file :
                json.dump(json_data, file, indent=4)

            # 刷新大图
            init_image_rate = copy.deepcopy(self.image_rate)
            self.loadImage()
            self.matchButtonSize()
            self.object.manga_ui.setImageInitRate(init_image_rate)
            # 刷新编辑框译图列表框
            self.object.manga_ui.editImageWidgetRefreshImage(self.original_image_path)
            self.object.manga_ui.transImageWidgetRefreshImage(self.original_image_path)


        except Exception as err :
            self.logger.error(traceback.format_exc())
            utils.message.MessageBox("手动识别失败", traceback.format_exc(), self.rate)
            self.paint_button.deleteLater()
        finally :
            if self.paint_status :
                self.manualOCR()


    # 绘制区域结束执行区域还原
    def paintAreaRecoverReset(self, sign) :

        try :
            if not self.paint_button :
                if self.paint_status :
                    self.areaRecover()
                return
            # 如果框太小就直接删掉, 防止误操作绘制出错误的框
            if self.paint_button.width() <= 10 and self.paint_button.height() <= 10 :
                self.paint_button.deleteLater()
                if self.paint_status :
                    self.areaRecover()
                return

            # 计算坐标
            x = int(self.paint_button.x() / self.image_rate[0])
            y = int(self.paint_button.y() / self.image_rate[1])
            w = int(self.paint_button.width() / self.image_rate[0])
            h = int(self.paint_button.height() / self.image_rate[1])
            # 打开原图, 按照坐标截图
            original_image = Image.open(self.original_image_path)
            original_cut_image = original_image.crop((x, y, x+w, y+h))
            # 打开ipt图, 将原图贴于ipt图上
            ipt_image = Image.open(self.ipt_image_path)
            ipt_image.paste(original_cut_image, (x, y))
            ipt_image.save(self.ipt_image_path)
            # 打开rdr图, 将原图贴于rdr图上
            rdr_image = Image.open(self.image_path)
            rdr_image.paste(original_cut_image, (x, y))
            rdr_image.save(self.image_path)

            # 刷新大图
            init_image_rate = copy.deepcopy(self.image_rate)
            self.loadImage()
            self.matchButtonSize()
            self.object.manga_ui.setImageInitRate(init_image_rate)
            # 刷新编辑框译图列表框
            self.object.manga_ui.editImageWidgetRefreshImage(self.original_image_path)
            self.object.manga_ui.transImageWidgetRefreshImage(self.original_image_path)

        except Exception as err :
            self.logger.error(traceback.format_exc())
            utils.message.MessageBox("区域还原失败", traceback.format_exc(), self.rate)
        finally :
            if self.paint_status :
                self.paint_button.deleteLater()
                self.areaRecover()


    # 加载大图
    def loadImage(self) :

        if not os.path.exists(self.image_path) :
            return
        self.image_pixmap = self.object.manga_ui.fromImageToPixmap(self.image_path)
        self.matchImageSize()


    # 点击文本框
    def clickTextBlock(self, button) :

        self.trans_edit_ui.button = button

        # 文本颜色
        font_color = QColor(button.font_color[0], button.font_color[1], button.font_color[2])
        self.trans_edit_ui.font_color = font_color.name()
        self.trans_edit_ui.font_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=font_color.name()))
        # 轮廓颜色
        bg_color = QColor(button.bg_color[0], button.bg_color[1], button.bg_color[2])
        self.trans_edit_ui.bg_color = bg_color.name()
        self.trans_edit_ui.bg_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=bg_color.name()))
        # 原文
        self.trans_edit_ui.original_text.clear()
        self.trans_edit_ui.original_text.insertPlainText(button.original)
        # 译文
        self.trans_edit_ui.trans_text.clear()
        self.trans_edit_ui.trans_text.insertPlainText(button.trans)
        # 字体样式
        self.trans_edit_ui.font_box.setCurrentText(button.font_type)
        # 轮廓宽度
        self.trans_edit_ui.shadow_size_spinbox.setValue(button.shadow_size)
        # 字体大小
        self.trans_edit_ui.text_size_spinbox.setValue(button.text_size)

        self.trans_edit_ui.show()


    # 图片自适配比例
    def matchImageSize(self) :

        try :
            pixmap = self.image_pixmap
            if pixmap.height() > self.height() :
                rate = self.height() / pixmap.height()
                pixmap = pixmap.scaled(pixmap.width()*rate, pixmap.height()*rate)
            if pixmap.width() > self.width() :
                rate = self.width() / pixmap.width()
                pixmap = pixmap.scaled(pixmap.width()*rate, pixmap.height()*rate)
            self.image_label.setPixmap(pixmap)

            self.image_rate = [
                pixmap.width() / self.image_pixmap.width(),
                pixmap.height() / self.image_pixmap.height()
            ]
            self.rate_label.setText("{}%".format(round(self.image_rate[0] * 100)))
        except Exception :
            self.logger.error(traceback.format_exc())


    # 文本框按钮自适配比例
    def matchButtonSize(self) :

        for button in self.button_list :
            # 计算缩放比例
            x = button.rect[0] * self.image_rate[0]
            y = button.rect[1] * self.image_rate[1]
            w = button.rect[2] * self.image_rate[0]
            h = button.rect[3] * self.image_rate[1]
            button.setGeometry(x, y, w, h)


    # 鼠标滚轮信号
    def wheelEvent(self, event) :

        if event.angleDelta().y() > 0 :
            if (self.image_rate[0] > 3 or self.image_rate[1] > 3) :
                return
            self.image_rate[0] += 0.1
            self.image_rate[1] += 0.1
        else :
            if (self.image_rate[0] < 0.1 or self.image_rate[1] < 0.1) :
                return
            self.image_rate[0] -= 0.1
            self.image_rate[1] -= 0.1

        pixmap = self.image_pixmap.scaled(
            self.image_pixmap.width() * self.image_rate[0],
            self.image_pixmap.height() * self.image_rate[1]
        )
        self.image_label.setPixmap(pixmap)
        self.rate_label.setText("{}%".format(round(self.image_rate[0] * 100)))
        self.matchButtonSize()


    # 窗口尺寸变化信号
    def resizeEvent(self, event) :

        w = event.size().width()
        h = event.size().height()
        w_rate = w / 1000
        h_rete = h / 635
        self.scroll_area.setGeometry(0, 0, w, h)
        self.matchImageSize()
        self.matchButtonSize()
        self.rate_label.setGeometry(930*w_rate, 590*h_rete, 60*w_rate, 30*h_rete)
        self.manual_ocr_button.setGeometry(0, 590*h_rete, 100*w_rate, 30*h_rete)
        self.area_recover_button.setGeometry(100*w_rate, 590*h_rete, 100*w_rate, 30*h_rete)


    # 文字块按钮右键菜单
    def showTextBlockButtonMenu(self, button) :

        menu = QMenu(self)
        delete_action = menu.addAction("删除")
        delete_action.triggered.connect(lambda: self.deleteTextBlock(button))
        cursorPos = QCursor.pos()
        menu.exec_(cursorPos)


    # 删除文本块
    def deleteTextBlock(self, button) :

        try :
            # 打开原图, 按照文本块坐标截图
            image = Image.open(self.original_image_path)
            x, y, w, h = button.rect[0], button.rect[1], button.rect[2], button.rect[3]
            cropped_image = image.crop((x, y, x + w, y + h))
            # 打开rdr图片, 将截图贴图
            rdr_image = Image.open(self.image_path)
            rdr_image.paste(cropped_image, (x, y))
            rdr_image.save(self.image_path)

            # 刷新缓存文件中获取json结果
            file_name = os.path.splitext(os.path.basename(self.original_image_path))[0]
            json_file_path = os.path.join(os.path.dirname(self.ipt_image_path), "%s.json"%file_name)
            with open(json_file_path, "r", encoding="utf-8") as file :
                json_data = json.load(file)
            if "translated_text" in json_data :
                if len(json_data["translated_text"]) > button.index :
                    del json_data["translated_text"][button.index]
            if "text_block" in json_data :
                if len(json_data["text_block"]) > button.index :
                    del json_data["text_block"][button.index]
            # 缓存ocr结果
            with open(json_file_path, "w", encoding="utf-8") as file :
                json.dump(json_data, file, indent=4)
            # 删除文本框按钮
            button.close()
            del self.button_list[button.index]
            # 刷新文本框按钮索引值
            for i, button in enumerate(self.button_list) :
                button.index = i
            # 刷新大图
            init_image_rate = copy.deepcopy(self.image_rate)
            self.loadImage()
            self.matchButtonSize()
            self.object.manga_ui.setImageInitRate(init_image_rate)

            # 刷新编辑框译图列表框
            self.object.manga_ui.editImageWidgetRefreshImage(self.original_image_path)
            self.object.manga_ui.transImageWidgetRefreshImage(self.original_image_path)

        except Exception :
            self.logger.error(traceback.format_exc())
            utils.message.MessageBox("删除文本块失败", traceback.format_exc(), self.rate)


    # 移动文本块位置后重新渲染
    def refreshTextBlockPosition(self, button) :

        try :
            # 原坐标
            x_0 = button.rect[0]
            y_0 = button.rect[1]
            w_0 = button.rect[2]
            h_0 = button.rect[3]
            # 当前坐标
            x_n = round(button.x() / self.image_rate[0])
            y_n = round(button.y() / self.image_rate[1])
            w_n = w_0
            h_n = h_0

            # 基于原坐标, 对ipt截图
            ipt_image = Image.open(self.ipt_image_path)
            cropped_image = ipt_image.crop((x_0, y_0, x_0 + w_0, y_0 + h_0))
            # 打开rdr图片, 将截图贴图
            rdr_image = Image.open(self.image_path)
            rdr_image.paste(cropped_image, (x_0, y_0))

            # 新位置ipt截图
            cropped_image = ipt_image.crop((x_n, y_n, x_n + w_n, y_n + h_n))
            # 截图转换为base64
            buffered = io.BytesIO()
            cropped_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            # 重新计算截图后的坐标
            text_block = copy.deepcopy(button.text_block)
            diff_w = text_block["block_coordinate"]["upper_left"][0]
            diff_h = text_block["block_coordinate"]["upper_left"][1]

            x_list, y_list = [], []
            for i, val in enumerate(text_block["coordinate"]):
                coordinate = {}
                for k in val.keys() :
                    coordinate[k] = [val[k][0] - diff_w, val[k][1] - diff_h]
                    x_list.append(coordinate[k][0])
                    y_list.append(coordinate[k][1])
                text_block["coordinate"][i] = coordinate

            text_block["block_coordinate"]["upper_left"] = [min(x_list), min(y_list)]
            text_block["block_coordinate"]["upper_right"] = [max(x_list), min(y_list)]
            text_block["block_coordinate"]["lower_right"] = [max(x_list), max(y_list)]
            text_block["block_coordinate"]["lower_left"] = [min(x_list), max(y_list)]

            # 调用漫画rdr
            sign, result = translator.ocr.dango.mangaRDR(
                object=self.object,
                trans_list=[button.trans],
                inpainted_image=image_base64,
                text_block=[text_block],
                font=button.font_type,
                check_permission=self.object.manga_ui.check_permission
            )
            if not sign or not result.get("rendered_image", ""):
                utils.message.MessageBox("移动文本块失败", result, self.rate)
                return

            # 渲染后的新图贴在rdr大图上
            image_base64 = base64.b64decode(result["rendered_image"])
            cropped_image = Image.open(io.BytesIO(image_base64))
            rdr_image.paste(cropped_image, (x_n, y_n))
            rdr_image.save(self.image_path)

            # 获取文件名
            file_name = os.path.splitext(os.path.basename(self.original_image_path))[0]
            # 获取ocr缓存文件路径
            json_file_path = os.path.join(os.path.dirname(self.ipt_image_path), "%s.json"%file_name)
            # 从缓存文件中获取ocr信息
            with open(json_file_path, "r", encoding="utf-8") as file :
                json_data = json.load(file)

            # 修改移动后的block_coordinate
            block_coordinate = json_data["text_block"][button.index]["block_coordinate"]
            block_coordinate["upper_left"] = [x_n, y_n]
            block_coordinate["upper_right"] = [x_n + w_n, y_n]
            block_coordinate["lower_right"] = [x_n + w_n, y_n + h_n]
            block_coordinate["lower_left"] = [x_n, y_n + h_n]
            json_data["text_block"][button.index]["block_coordinate"] = block_coordinate

            # 修改移动后的coordinate
            coordinate = json_data["text_block"][button.index]["coordinate"]
            for i, val in enumerate(coordinate) :
                tmp_coordinate = {}
                for k in val.keys() :
                    tmp_coordinate[k] = [
                        val[k][0] - (x_0 - x_n),
                        val[k][1] - (y_0 - y_n)
                    ]
                coordinate[i] = tmp_coordinate
            json_data["text_block"][button.index]["coordinate"] = coordinate

            # 缓存修改后的ocr结果
            with open(json_file_path, "w", encoding="utf-8") as file :
                json.dump(json_data, file, indent=4)

            # 刷新按钮信息
            button.rect = (x_n, y_n, w_n, h_n)
            button.text_block = json_data["text_block"][button.index]
            # 刷新大图
            init_image_rate = copy.deepcopy(self.image_rate)
            self.loadImage()
            self.matchButtonSize()
            self.object.manga_ui.setImageInitRate(init_image_rate)
            # 刷新编辑框译图列表框
            self.object.manga_ui.editImageWidgetRefreshImage(self.original_image_path)
            self.object.manga_ui.transImageWidgetRefreshImage(self.original_image_path)

        except Exception :
            self.logger.error(traceback.format_exc())
            utils.message.MessageBox("移动文本块失败", traceback.format_exc(), self.rate)

    # 手动OCR
    def manualOCR(self) :

        self.paint_status = not self.paint_status
        self.paint_button = None
        self.image_label.paint_type = "ocr"

        if self.paint_status :
            # 按下手动OCR按钮
            self.area_recover_button.setEnabled(False)
            self.scroll_area.paint_status = True
            self.image_label.paint_status = True
            self.scroll_area.setCursor(Qt.CrossCursor)
            self.image_label.setCursor(Qt.CrossCursor)
            self.manual_ocr_button.setStyleSheet("background-color: #83AAF9; color: #FFFFFF;")
            if not self.object.manga_ui.hide_image_widget_status :
                self.object.manga_ui.last_page_button.hide()
                self.object.manga_ui.next_page_button.hide()
        else :
            # 释放手动OCR按钮
            self.area_recover_button.setEnabled(True)
            self.scroll_area.paint_status = False
            self.image_label.paint_status = False
            self.scroll_area.setCursor(Qt.OpenHandCursor)
            self.image_label.setCursor(Qt.OpenHandCursor)
            self.manual_ocr_button.setStyleSheet("QPushButton {color: #5B8FF9;}"
                                                 "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                                 "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
            if not self.object.manga_ui.hide_image_widget_status :
                self.object.manga_ui.last_page_button.show()
                self.object.manga_ui.next_page_button.show()


    # 点击区域还原按钮
    def areaRecover(self) :

        self.paint_status = not self.paint_status
        self.paint_button = None
        self.image_label.paint_type = "recover"

        if self.paint_status :
            # 按下区域还原按钮
            self.manual_ocr_button.setEnabled(False)
            self.scroll_area.paint_status = True
            self.image_label.paint_status = True
            self.scroll_area.setCursor(Qt.CrossCursor)
            self.image_label.setCursor(Qt.CrossCursor)
            self.area_recover_button.setStyleSheet("background-color: #83AAF9; color: #FFFFFF;")
            if not self.object.manga_ui.hide_image_widget_status :
                self.object.manga_ui.last_page_button.hide()
                self.object.manga_ui.next_page_button.hide()
        else:
            # 释放区域还原按钮
            self.manual_ocr_button.setEnabled(True)
            self.scroll_area.paint_status = False
            self.image_label.paint_status = False
            self.scroll_area.setCursor(Qt.OpenHandCursor)
            self.image_label.setCursor(Qt.OpenHandCursor)
            self.area_recover_button.setStyleSheet("QPushButton {color: #5B8FF9;}"
                                                   "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
                                                   "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}")
            if not self.object.manga_ui.hide_image_widget_status :
                self.object.manga_ui.last_page_button.show()
                self.object.manga_ui.next_page_button.show()


# 译文编辑界面
class TransEdit(QWidget) :

    def __init__(self, object) :

        super(TransEdit, self).__init__()
        self.object = object
        self.rate = object.yaml["screen_scale_rate"]
        self.logger = object.logger
        self.font_color = "#83AAF9"
        self.bg_color = "#83AAF9"
        self.button = None
        self.font_list = [
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Regular",
            "阿里/东方大楷/Alimama_DongFangDaKai_Regular",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_55_Regular_55_Regular",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Bold",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Medium_Italic",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Regular_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Regular",
            "书法/庞门正道真贵楷体",
            "书法/钟齐志莽行书",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Black",
            "阿里/数黑体/Alimama_ShuHeiTi_Bold",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Regular_Italic",
            "Noto_Sans_SC/NotoSansSC-Black",
            "黑体/Leefont蒙黑体",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Black",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Bold",
            "Noto_Sans_SC/NotoSansSC-Light",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_105_Heavy_105_Heavy",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Light",
            "书法/演示秋鸿楷",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Thin",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Bold_Italic",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Light",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_55_Regular_85_Bold",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Medium",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Thin",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Regular",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Light",
            "Emoji/NotoColorEmoji",
            "书法/仓耳周珂正大榜书",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Medium_Italic",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_35_Thin_35_Thin",
            "书法/鸿雷板书简体-Regular",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Regular",
            "黑体/千图厚黑体",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Black",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Bold_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Medium",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Light",
            "书法/庞门正道粗书体",
            "书法/钟齐流江毛草",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_115_Black_115_Black",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Bold",
            "黑体/标小智无界黑",
            "书法/演示夏行楷",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_45_Light_45_Light",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Medium",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Black",
            "黑体/Aa厚底黑",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Black_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Bold",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Light_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Light",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Thin_Italic",
            "书法/演示佛系体",
            "Noto_Sans_SC/NotoSansSC-Regular",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Light",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Medium",
            "书法/演示春风楷",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Thin",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Black_Italic",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Regular",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Medium",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Regular",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Medium",
            "Noto_Sans_SC/NotoSansSC-Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_65_Medium_65_Medium",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_75_SemiBold_75_SemiBold",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Thin",
            "Noto_Sans_SC/NotoSansSC-Bold",
            "Noto_Sans_SC/NotoSansSC-Medium",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Black",
            "书法/江西拙楷2.0",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Thin_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Bold",
            "阿里/钉钉进步体/DingTalk_JinBuTi_Regular",
            "书法/演示悠然小楷",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_95_ExtraBold_95_ExtraBold",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Black",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Light_Italic",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Bold"
        ]
        self.trans_type_map = {
            "团子": "dango_private",
            "彩云": "caiyun_private",
            "腾讯": "tencent_private",
            "百度": "baidu_private",
            "ChatGPT": "chatgpt_private",
            "阿里": "aliyun_private",
            "有道": "youdao_private",
            "小牛": "xiaoniu_private",
            "火山": "huoshan_private",
        }
        self.ui()


    def ui(self) :

        # 窗口尺寸及不可拉伸
        self.window_width = int(500*self.rate)
        self.window_height = int(360*self.rate)
        self.resize(self.window_width, self.window_height)
        self.setMinimumSize(QSize(self.window_width, self.window_height))
        self.setMaximumSize(QSize(self.window_width, self.window_height))
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)

        # 窗口标题
        self.setWindowTitle("图片翻译-译文编辑")
        # 窗口图标
        self.setWindowIcon(ui.static.icon.APP_LOGO_ICON)
        # 鼠标样式
        self.setCursor(ui.static.icon.PIXMAP_CURSOR)
        # 设置字体
        font_type = "华康方圆体W7"
        try :
            id = QFontDatabase.addApplicationFont(FONT_PATH_1)
            font_list = QFontDatabase.applicationFontFamilies(id)
            font_type = font_list[0]
        except Exception :
            pass

        # 控件样式
        self.setStyleSheet(
            "QLabel {background: transparent; font: 9pt '华康方圆体W7'; color: #5B8FF9;}"
            "QPushButton {background: transparent; font: 9pt '华康方圆体W7'; color: #5B8FF9;}"
            "QPushButton:hover {background-color: #83AAF9; color: #FFFFFF;}"
            "QPushButton:pressed {background-color: #83AAF9; color: #FFFFFF;}"
            "QMenu {color: #5B8FF9; background-color: #FFFFFF; font: 9pt '华康方圆体W7';}"
            "QMenu::item:selected:enabled {background: #E5F5FF;}"
            "QMenu::item:checked {background: #E5F5FF;}"
            "QComboBox QAbstractItemView::item { min-height:40px; }"
            "QDoubleSpinBox {background: transparent; font: 9pt '华康方圆体W7'; color: #5B8FF9;}"
            "QSpinBox {background: transparent; font: 9pt '华康方圆体W7'; color: #5B8FF9;}"
            "QTextBrowser {font: 12pt '%s';}"%font_type
        )

        # 私人彩云
        button = QPushButton(self)
        self.customSetGeometry(button, 0, 0, 80, 30)
        button.setCursor(ui.static.icon.EDIT_CURSOR)
        button.setText(" 彩云")
        button.setIcon(ui.static.icon.TRANSLATE_ICON)
        button.clicked.connect(lambda: self.refreshTrans("彩云"))
        button.setToolTip("<b>使用私人彩云重新翻译</b>")

        # 私人腾讯
        button = QPushButton(self)
        self.customSetGeometry(button, 80, 0, 80, 30)
        button.setCursor(ui.static.icon.EDIT_CURSOR)
        button.setText(" 腾讯")
        button.setIcon(ui.static.icon.TRANSLATE_ICON)
        button.clicked.connect(lambda: self.refreshTrans("腾讯"))
        button.setToolTip("<b>使用私人腾讯重新翻译</b>")

        # 私人百度
        button = QPushButton(self)
        self.customSetGeometry(button, 160, 0, 80, 30)
        button.setCursor(ui.static.icon.EDIT_CURSOR)
        button.setText(" 百度")
        button.setIcon(ui.static.icon.TRANSLATE_ICON)
        button.clicked.connect(lambda: self.refreshTrans("百度"))
        button.setToolTip("<b>使用私人百度重新翻译</b>")

        # 私人ChatGPT
        button = QPushButton(self)
        self.customSetGeometry(button, 240, 0, 80, 30)
        button.setCursor(ui.static.icon.EDIT_CURSOR)
        button.setText(" ChatGPT")
        button.setIcon(ui.static.icon.TRANSLATE_ICON)
        button.clicked.connect(lambda: self.refreshTrans("ChatGPT"))
        button.setToolTip("<b>使用私人ChatGPT重新翻译</b>")

        # 其他翻译按钮
        self.select_trans_button = QPushButton(self)
        self.customSetGeometry(self.select_trans_button, 320, 0, 80, 30)
        self.select_trans_button.setCursor(ui.static.icon.EDIT_CURSOR)
        self.select_trans_button.setText(" 其他")
        self.select_trans_button.setIcon(ui.static.icon.TRANSLATE_ICON)
        button.setToolTip("<b>选择使用的翻译源重新翻译</b>")
        # 翻译源菜单
        self.trans_menu = QMenu(self.select_trans_button)
        self.trans_menu.setCursor(ui.static.icon.PIXMAP_CURSOR)
        self.trans_action_group = QActionGroup(self.trans_menu)
        self.trans_action_group.setExclusive(True)
        self.createTransAction("团子")
        self.createTransAction("阿里")
        self.createTransAction("有道")
        self.createTransAction("小牛")
        self.createTransAction("火山")
        # 将下拉菜单设置为按钮的菜单
        self.select_trans_button.setMenu(self.trans_menu)
        self.trans_action_group.triggered.connect(self.selectTrans)

        # 修改字体颜色
        self.font_color_button = QPushButton(qtawesome.icon("fa5s.paint-brush", color=self.font_color), "", self)
        self.customSetGeometry(self.font_color_button, 0, 30, 80, 30)
        self.font_color_button.setCursor(ui.static.icon.EDIT_CURSOR)
        self.font_color_button.setText(" 字体色")
        self.font_color_button.clicked.connect(self.changeTranslateColor)
        self.font_color_button.setToolTip("<b>修改显示的字体颜色</b>")

        # 修改轮廓颜色
        self.bg_color_button = QPushButton(qtawesome.icon("fa5s.paint-brush", color=self.bg_color), "", self)
        self.customSetGeometry(self.bg_color_button, 80, 30, 80, 30)
        self.bg_color_button.setCursor(ui.static.icon.EDIT_CURSOR)
        self.bg_color_button.setText(" 轮廓色")
        self.bg_color_button.clicked.connect(self.changeBackgroundColor)
        self.bg_color_button.setToolTip("<b>修改显示的轮廓颜色</b>")

        # 轮廓宽度设定
        self.shadow_size_spinbox = QDoubleSpinBox(self)
        self.customSetGeometry(self.shadow_size_spinbox, 170, 35, 40, 20)
        self.shadow_size_spinbox.setDecimals(1)
        self.shadow_size_spinbox.setSingleStep(0.1)
        self.shadow_size_spinbox.setMinimum(0)
        self.shadow_size_spinbox.setMaximum(16)
        self.shadow_size_spinbox.setValue(4)
        self.shadow_size_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        label = QLabel(self)
        self.customSetGeometry(label, 220, 37, 100, 20)
        label.setText("轮廓宽度")

        # 字体大小设定
        self.text_size_spinbox = QSpinBox(self)
        self.customSetGeometry(self.text_size_spinbox, 290, 35, 40, 20)
        self.text_size_spinbox.setMinimum(16)
        self.text_size_spinbox.setMaximum(512)
        self.text_size_spinbox.setValue(40)
        self.text_size_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        label = QLabel(self)
        self.customSetGeometry(label, 340, 37, 100, 20)
        label.setText("字体大小")

        # 字体样式
        label = QLabel(self)
        self.customSetGeometry(label, 10, 65, 20, 20)
        label.setPixmap(ui.static.icon.FONT_PIXMAP)
        self.font_box = QComboBox(self)
        self.customSetGeometry(self.font_box, 30, 62, 390, 25)
        self.font_box.setCursor(ui.static.icon.EDIT_CURSOR)
        self.font_box.view().setCursor(ui.static.icon.PIXMAP_CURSOR)
        self.font_box.setToolTip("<b>设置字体样式</b>")

        # 支持编辑和搜索
        self.font_box.setEditable(True)
        line_edit = QLineEdit()
        completer = self.font_box.completer()
        line_edit.setCompleter(completer)
        self.font_box.setItemDelegate(QStyledItemDelegate())
        utils.thread.createThread(self.createFontBox)

        # 原文编辑框
        self.original_text = QTextBrowser(self)
        self.customSetGeometry(self.original_text, 0, 90, 500, 100)
        self.original_text.setReadOnly(False)
        self.original_text.setCursor(ui.static.icon.EDIT_CURSOR)

        # 原文复制按钮
        button = QPushButton(self)
        self.customSetGeometry(button, 480, 170, 20, 20)
        button.setIcon(ui.static.icon.COPY_ICON)
        self.customSetIconSize(button, 20, 20)
        button.setStyleSheet("QPushButton {background: transparent; border-radius: 6px}"
                             "QPushButton:hover {background-color: #83AAF9;}"
                             "QPushButton:pressed {background-color: #4480F9;}")
        button.setToolTip("<b>复制当前原文</b>")
        button.clicked.connect(lambda: pyperclip.copy(self.original_text.toPlainText()))

        # 译文编辑框
        self.trans_text = QTextBrowser(self)
        self.customSetGeometry(self.trans_text, 0, 190, 500, 100)
        self.trans_text.setCursor(ui.static.icon.EDIT_CURSOR)
        self.trans_text.setReadOnly(False)
        self.trans_text.setCursor(ui.static.icon.EDIT_CURSOR)

        # 译文复制按钮
        button = QPushButton(self)
        self.customSetGeometry(button, 480, 270, 20, 20)
        button.setIcon(ui.static.icon.COPY_ICON)
        self.customSetIconSize(button, 20, 20)
        button.setStyleSheet("QPushButton {background: transparent; border-radius: 6px}"
                             "QPushButton:hover {background-color: #83AAF9;}"
                             "QPushButton:pressed {background-color: #4480F9;}")
        button.setToolTip("<b>复制当前译文</b>")
        button.clicked.connect(lambda: pyperclip.copy(self.trans_text.toPlainText()))

        # 重新贴字按钮
        button = QPushButton(self)
        self.customSetGeometry(button, 200, 300, 100, 50)
        button.setText("重新贴字")
        button.setStyleSheet("font: 12pt '华康方圆体W7';")
        button.clicked.connect(self.renderTextBlock)
        button.setCursor(ui.static.icon.SELECT_CURSOR)


    # 根据分辨率定义控件位置尺寸
    def customSetGeometry(self, object, x, y, w, h) :

        object.setGeometry(QRect(int(x * self.rate),
                                 int(y * self.rate), int(w * self.rate),
                                 int(h * self.rate)))

    # 根据分辨率定义图标位置尺寸
    def customSetIconSize(self, object, w, h) :

        object.setIconSize(QSize(int(w * self.rate), int(h * self.rate)))


    # 重新渲染文字
    def renderTextBlock(self) :

        try :
            if not self.button :
                return

            # 打开ipt图片, 按照文本块坐标截图
            image = Image.open(self.button.ipt_image_path)
            x = self.button.rect[0]
            y = self.button.rect[1]
            w = self.button.rect[2]
            h = self.button.rect[3]
            cropped_image = image.crop((x, y, x + w, y + h))

            # 截图转换为base64
            buffered = io.BytesIO()
            cropped_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

            text_block = copy.deepcopy(self.button.text_block)
            # 修改字体颜色
            color = QColor(self.font_color)
            f_r, f_g, f_b, f_a = color.getRgb()
            text_block["foreground_color"] = [f_r, f_g, f_b]
            # 修改轮廓颜色
            color = QColor(self.bg_color)
            b_r, b_g, b_b, b_a = color.getRgb()
            text_block["background_color"] = [b_r, b_g, b_b]

            # 重新计算截图后的坐标
            diff_w = text_block["block_coordinate"]["upper_left"][0]
            diff_h = text_block["block_coordinate"]["upper_left"][1]
            x_list, y_list = [], []
            for i, val in enumerate(text_block["coordinate"]):
                coordinate = {}
                for k in val.keys():
                    coordinate[k] = [val[k][0] - diff_w, val[k][1] - diff_h]
                    x_list.append(coordinate[k][0])
                    y_list.append(coordinate[k][1])
                text_block["coordinate"][i] = coordinate

            text_block["block_coordinate"]["upper_left"] = [min(x_list), min(y_list)]
            text_block["block_coordinate"]["upper_right"] = [max(x_list), min(y_list)]
            text_block["block_coordinate"]["lower_right"] = [max(x_list), max(y_list)]
            text_block["block_coordinate"]["lower_left"] = [min(x_list), max(y_list)]

            # 轮廓宽度
            text_block["shadow_size"] = self.shadow_size_spinbox.value()
            # 字体大小
            text_block["text_size"] = self.text_size_spinbox.value()

            # 漫画rdr
            sign, result = translator.ocr.dango.mangaRDR(
                object=self.object,
                trans_list=[self.trans_text.toPlainText()],
                inpainted_image=image_base64,
                text_block=[text_block],
                font=self.font_box.currentText(),
                check_permission=self.object.manga_ui.check_permission
            )
            if not sign or not result.get("rendered_image", "") :
                utils.message.MessageBox("重新贴字失败", result, self.rate)
                return

            # 渲染后的新图贴在大图上
            image_base64 = base64.b64decode(result["rendered_image"])
            cropped_image = Image.open(io.BytesIO(image_base64))
            rdr_image = Image.open(self.button.rdr_image_path)
            rdr_image.paste(cropped_image, (x, y))
            rdr_image.save(self.button.rdr_image_path)

            # 刷新缓存文件中获取json结果
            file_name = os.path.splitext(os.path.basename(self.button.original_image_path))[0]
            json_file_path = os.path.join(os.path.dirname(self.button.ipt_image_path), "%s.json"%file_name)
            with open(json_file_path, "r", encoding="utf-8") as file :
                json_data = json.load(file)

            # 过滤translated_text长度和text_block长度不一致的情况
            if "translated_text" not in json_data :
                json_data["translated_text"] = []
                for _ in range(len(json_data["text_block"])) :
                    json_data["translated_text"].append("")
            if len(json_data["translated_text"]) < self.button.index+1 :
                diff_index = self.button.index+1 - len(json_data["translated_text"])
                for _ in range(diff_index) :
                    json_data["translated_text"].append("")

            json_data["translated_text"][self.button.index] = self.trans_text.toPlainText()
            json_data["text_block"][self.button.index]["foreground_color"] = [f_r, f_g, f_b]
            json_data["text_block"][self.button.index]["background_color"] = [b_r, b_g, b_b]
            json_data["text_block"][self.button.index]["font_selector"] = self.font_box.currentText()
            json_data["text_block"][self.button.index]["shadow_size"] = self.shadow_size_spinbox.value()
            json_data["text_block"][self.button.index]["text_size"] = self.text_size_spinbox.value()

            # 缓存ocr结果
            with open(json_file_path, "w", encoding="utf-8") as file :
                json.dump(json_data, file, indent=4)

            # 刷新文本块按钮信息
            self.button.text_block = json_data["text_block"][self.button.index]
            self.button.trans = self.trans_text.toPlainText()
            self.button.font_color = [f_r, f_g, f_b]
            self.button.bg_color = [b_r, b_g, b_b]
            self.button.font_type = self.font_box.currentText()
            self.button.shadow_size = self.shadow_size_spinbox.value()
            self.button.text_size = self.text_size_spinbox.value()

            # 刷新大图
            init_image_rate = copy.deepcopy(self.object.manga_ui.show_image_widget.image_rate)
            self.object.manga_ui.show_image_widget.loadImage()
            self.object.manga_ui.show_image_widget.matchButtonSize()
            self.object.manga_ui.setImageInitRate(init_image_rate)
            # 刷新编辑框译图列表框
            self.object.manga_ui.editImageWidgetRefreshImage(self.button.original_image_path)
            self.object.manga_ui.transImageWidgetRefreshImage(self.button.original_image_path)

        except Exception :
            self.logger.error(traceback.format_exc())
            utils.message.MessageBox("重新贴字失败", traceback.format_exc(), self.rate)


    # 刷新翻译结果
    def refreshTrans(self, trans_type) :

        original = self.original_text.toPlainText()
        if not original.strip() :
            return
        # 翻译源
        trans_type = self.trans_type_map[trans_type]

        # 从数据库中获取翻译结果
        trans_map = {}
        if self.object.config["transHistoryUse"] :
            trans_map = utils.sqlite.selectTranslationDBBySrcAndTransType(original, self.logger)
            # 是否使用模糊匹配
            if not self.object.config["transHistoryPerfectUse"] and self.object.yaml["similar_score"] < 100 and not trans_map :
                similar_original = utils.sqlite.selectTransDataBySimilarity(original, self.object.yaml["similar_score"], self.logger)
                if similar_original:
                    trans_map = utils.sqlite.selectTranslationDBBySrcAndTransType(similar_original, self.logger)

        if trans_type in trans_map :
            result = trans_map[trans_type]
        else :
            # 调用翻译
            if trans_type == "dango_private" :
                sign, result = translator.ocr.dango.dangoTrans(
                    object=self.object,
                    sentence=original,
                    language=self.object.config["mangaLanguage"]
                )
                if not sign :
                    utils.message.MessageBox("私人团子翻译失败", result, self.rate)
                    return

            elif trans_type == "caiyun_private" :
                result = translator.api.caiyun(
                    sentence=original,
                    token=self.object.config["caiyunAPI"],
                    logger=self.logger
                )
                if re.match("^私人彩云[:：]", result) :
                    utils.message.MessageBox("私人彩云翻译失败", result, self.rate)
                    return

            elif trans_type == "tencent_private" :
                result = translator.api.tencent(
                    sentence=original,
                    secret_id=self.object.config["tencentAPI"]["Key"],
                    secret_key=self.object.config["tencentAPI"]["Secret"],
                    logger=self.logger
                )
                if re.match("^私人腾讯[:：]", result) :
                    utils.message.MessageBox("私人腾讯翻译失败", result, self.rate)
                    return

            elif trans_type == "baidu_private" :
                result = translator.api.baidu(
                    sentence=original,
                    app_id=self.object.config["baiduAPI"]["Key"],
                    secret_key=self.object.config["baiduAPI"]["Secret"],
                    logger=self.logger
                )
                if re.match("^私人百度[:：]", result) :
                    utils.message.MessageBox("私人百度翻译失败", result, self.rate)
                    return

            elif trans_type == "chatgpt_private" :
                result = translator.api.chatgpt(
                    object=self.object,
                    content=original,
                    delay_time=0,
                )
                if re.match("^私人ChatGPT[:：]", result) :
                    utils.message.MessageBox("私人ChatGPT翻译失败", result, self.rate)
                    return

            elif trans_type == "aliyun_private" :
                sign, result = translator.api.aliyun(
                    access_key_id=self.object.config["aliyunAPI"]["Key"],
                    access_key_secret=self.object.config["aliyunAPI"]["Secret"],
                    source_language=self.object.config["mangaLanguage"],
                    text_to_translate=original,
                    logger=self.object.logger
                )
                if not sign :
                    utils.message.MessageBox("私人阿里翻译失败", result, self.rate)
                    return

            elif trans_type == "youdao_private" :
                sign, result = translator.api.youdao(
                    text=original,
                    app_key=self.object.config["youdaoAPI"]["Key"],
                    app_secret=self.object.config["youdaoAPI"]["Secret"],
                    logger=self.object.logger
                )
                if not sign :
                    utils.message.MessageBox("私人有道翻译失败", result, self.rate)
                    return

            elif trans_type == "xiaoniu_private" :
                sign, result = translator.api.xiaoniu(
                    apikey=self.object.config["xiaoniuAPI"],
                    sentence=original,
                    language=self.object.config["mangaLanguage"],
                    logger=self.object.logger
                )
                if not sign :
                    utils.message.MessageBox("私人小牛翻译失败", result, self.rate)
                    return

            elif trans_type == "huoshan_private" :
                sign, result = translator.api.huoshan(
                    ak=self.object.config["huoshanAPI"]["Key"],
                    sk=self.object.config["huoshanAPI"]["Secret"],
                    text=original,
                    logger=self.object.logger
                )
                if not sign :
                    utils.message.MessageBox("私人火山翻译失败", result, self.rate)
                    return

            else :
                return
            # 翻译结果缓存到本地数据库
            utils.sqlite.insertTranslationDB(self.object.logger, original, trans_type, result)

        # 根据屏蔽词过滤
        for filter in self.object.config["Filter"]:
            if not filter[0] :
                continue
            result = result.replace(filter[0], filter[1])

        if result :
            self.trans_text.clear()
            self.trans_text.insertPlainText(result)


    # 修改字体颜色
    def changeTranslateColor(self) :

        self.hide()
        color = QColorDialog.getColor(QColor(self.font_color), None, "修改字体颜色")
        if color.isValid() :
            self.font_color = color.name()
            self.font_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=self.font_color))
        self.show()


    # 修改轮廓颜色
    def changeBackgroundColor(self):

        self.hide()
        color = QColorDialog.getColor(QColor(self.bg_color), None, "修改轮廓颜色")
        if color.isValid():
            self.bg_color = color.name()
            self.bg_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=self.bg_color))
        self.show()


    # 创建字体按钮的下拉菜单
    def createFontBox(self):

        sign, resp = translator.ocr.dango.mangaFontList(self.object)
        if sign :
            font_list = resp.get("available_fonts", [])
        else:
            font_list = copy.deepcopy(self.font_list)
        if not font_list :
            font_list = copy.deepcopy(self.font_list)

        for index, font in enumerate(font_list) :
            self.font_box.addItem("")
            self.font_box.setItemText(index, font)


    # 创建翻译源按钮的下拉菜单
    def createTransAction(self, label) :

        action = QAction(label, self.trans_menu)
        action.setCheckable(True)
        action.setData(label)
        self.trans_action_group.addAction(action)
        self.trans_menu.addAction(action)
        if self.object.config["mangaTrans"] == label:
            action.setChecked(True)


    # 使用其他翻译源
    def selectTrans(self, action) :

        self.refreshTrans(action.data())


# 根据文本块大小计算 font_size
def getFontSize(coordinate, trans_text) :

    lines = []
    for val in coordinate :
        line = []
        line.append(val["upper_left"])
        line.append(val["upper_right"])
        line.append(val["lower_right"])
        line.append(val["lower_left"])
        lines.append(line)

    line_x = [j[0] for i in lines for j in i]
    line_y = [j[1] for i in lines for j in i]
    w = max(line_x) - min(line_x)
    h = max(line_y) - min(line_y)


    def get_structure(pts) :

        p1 = [int((pts[0][0] + pts[1][0]) / 2), int((pts[0][1] + pts[1][1]) / 2)]
        p2 = [int((pts[2][0] + pts[3][0]) / 2), int((pts[2][1] + pts[3][1]) / 2)]
        p3 = [int((pts[1][0] + pts[2][0]) / 2), int((pts[1][1] + pts[2][1]) / 2)]
        p4 = [int((pts[3][0] + pts[0][0]) / 2), int((pts[3][1] + pts[0][1]) / 2)]
        return [p1, p2, p3, p4]


    def get_font_size(pts) -> float :

        [l1a, l1b, l2a, l2b] = [a for a in get_structure(pts)]
        v1 = [l1b[0] - l1a[0], l1b[1] - l1a[1]]
        v2 = [l2b[0] - l2a[0], l2b[1] - l2a[1]]
        return min(sqrt(v2[0] ** 2 + v2[1] ** 2), sqrt(v1[0] ** 2 + v1[1] ** 2))


    def findNextPowerOf2(n) :

        i = 0
        while n != 0:
            i += 1
            n = n >> 1
        return 1 << i

    font_size = int(min([get_font_size(pts) for pts in lines]))
    text_mag_ratio = 1

    font_size_enlarged = findNextPowerOf2(font_size) * text_mag_ratio
    enlarge_ratio = font_size_enlarged / font_size
    font_size = font_size_enlarged

    while True:
        enlarged_w = round(enlarge_ratio * w)
        enlarged_h = round(enlarge_ratio * h)
        rows = enlarged_h // (font_size * 1.3)
        cols = enlarged_w // (font_size * 1.3)
        if rows * cols < len(trans_text) :
            enlarge_ratio *= 1.1
            continue
        break

    return int(font_size / enlarge_ratio)


# 自定义按键实现鼠标进入显示, 移出隐藏
class CustomButton(QPushButton) :

    def __init__(self, text) :

        super().__init__(text)
        self.hide_status = False
        self.icon = QIcon()
        self.setStyleSheet("background: transparent;")


    # 设置隐藏状态
    def setHideStatus(self, hide_status, icon) :

        self.hide_status = hide_status
        self.icon = icon


    # 鼠标进入事件
    def enterEvent(self, a0) :

        if self.hide_status :
            self.setIcon(self.icon)
        self.setStyleSheet("background-color:rgba(62, 62, 62, 0.3)")
        self.show()
        return super().enterEvent(a0)

    # 鼠标移出事件
    def leaveEvent(self, a0) :

        if self.hide_status :
            self.setIcon(QIcon())
        self.setStyleSheet("background: transparent;")
        return super().leaveEvent(a0)


# 自定义QScrollArea禁用鼠标滚轮控制滚动条
class CustomScrollArea(QScrollArea) :

    def __init__(self, parent=None) :

        super().__init__(parent)
        self.paint_status = False


    # 取消事件的传递，禁用滚轮控制滚动条
    def wheelEvent(self, event) :

        event.ignore()


    # 鼠标移动事件
    def mouseMoveEvent(self, e: QMouseEvent) :

        try :
            if self.paint_status :
                return e.ignore()

            self._endPos = e.pos() - self._startPos
            horizontal = self.horizontalScrollBar()
            if self._endPos.x() > 3 :
                horizontal.setValue(horizontal.value() -3)
            else :
                horizontal.setValue(horizontal.value() +3)
            vertical = self.verticalScrollBar()
            if self._endPos.y() > 3 :
                vertical.setValue(vertical.value() -3)
            else :
                vertical.setValue(vertical.value() +3)
        except :
            pass


    # 鼠标按下事件
    def mousePressEvent(self, e: QMouseEvent) :

        try :
            if self.paint_status :
                return e.ignore()

            if e.button() == Qt.LeftButton :
                self._isTracking = True
                self._startPos = QPoint(e.x(), e.y())
                self.setCursor(Qt.ClosedHandCursor)
        except :
            pass


    # 鼠标松开事件
    def mouseReleaseEvent(self, e: QMouseEvent) :

        try :
            if self.paint_status :
                return e.ignore()
            if e.button() == Qt.LeftButton :
                self._isTracking = False
                self._startPos = None
                self._endPos = None
                self.setCursor(Qt.OpenHandCursor)
        except :
            pass


# 自定义TextBlock的按钮
class CustomTextBlockButton(QPushButton) :

    move_signal = pyqtSignal(QPushButton)
    click_signal = pyqtSignal(QPushButton)

    def __init__(self, text) :
        super().__init__(text)
        self._move = False
        self._isTracking = False
        self._startPos = None
        self._endPos = None


    # 参数初始化
    def initConfig(self, text_block, trans, rect, index, original_image_path,
                   ipt_image_path, rdr_image_path, font_type, shadow_size, text_size) :

        self.trans = trans
        self.text_block = text_block
        self.rect = rect
        self.index = index
        self.original_image_path = original_image_path
        self.ipt_image_path = ipt_image_path
        self.rdr_image_path = rdr_image_path
        self.font_type = font_type
        self.shadow_size = shadow_size
        self.text_size = text_size

        # 文本块信息
        self.original = ""
        for text in text_block["texts"]:
            self.original += text
        # 文字颜色
        self.font_color = text_block["foreground_color"]
        self.bg_color = text_block["background_color"]


    # 鼠标移动事件
    def mouseMoveEvent(self, e: QMouseEvent) :
        try :
            self._endPos = e.pos() - self._startPos
            self.move(self.pos() + self._endPos)
            self._move = True
        except Exception :
            pass


    # 鼠标按下事件
    def mousePressEvent(self, e: QMouseEvent) :
        try :
            if e.button() == Qt.LeftButton :
                self._isTracking = True
                self._startPos = QPoint(e.x(), e.y())
        except Exception :
            pass


    # 鼠标松开事件
    def mouseReleaseEvent(self, e: QMouseEvent) :
        try :
            if e.button() == Qt.LeftButton :
                if self._move :
                    # 移动事件
                    self.move_signal.emit(self)
                else :
                    # 点击事件
                    self.click_signal.emit(self)
                self._isTracking = False
                self._startPos = None
                self._endPos = None
                self._move = False

        except Exception :
            pass


# 高级设置界面
class Setting(QWidget) :

    def __init__(self, object) :

        super(Setting, self).__init__()
        self.object = object
        self.rate = object.yaml["screen_scale_rate"]
        self.logger = object.logger
        self.color_1 = "#595959"  # 灰色
        self.color_2 = "#5B8FF9"  # 蓝色
        self.detect_scale = self.object.config.get("mangaDetectScale", 1)
        self.merge_threshold = self.object.config.get("mangaMergeThreshold", 5)
        self.font_color = self.object.config.get("mangaFontColor", "#83AAF9")
        self.bg_color = self.object.config.get("mangaBgColor", "#83AAF9")
        self.font_color_use = self.object.config.get("mangaFontColorUse", False)
        self.bg_color_use = self.object.config.get("mangaBgColorUse", False)
        self.output_rename_use = self.object.config.get("mangaOutputRenameUse", False)
        self.fast_render_use = self.object.config.get("mangaFastRenderUse", False)
        self.filtrate_use = self.object.config.get("mangaFiltrateUse", True)
        self.shadow_size = self.object.config.get("mangaShadowSize", 4)
        self.font_size_use = self.object.config.get("mangaFontSizeUse", False)
        self.font_size = self.object.config.get("mangaFontSize", 36)
        self.auto_open_manga_use = self.object.yaml["auto_open_manga_use"]
        self.chatgpt_delay_use =  self.object.config.get("mangaChatgptDelayUse", False)
        self.chatgpt_delay_time = self.object.config.get("mangaChatgptDelayTime", 1)
        self.filter_char_use = self.object.config.get("mangaFilterCharUse", False)
        self.filter_char_count = self.object.config.get("mangaFilterCharCount", False)
        self.font_list = [
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Regular",
            "阿里/东方大楷/Alimama_DongFangDaKai_Regular",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_55_Regular_55_Regular",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Bold",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Medium_Italic",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Regular_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Regular",
            "书法/庞门正道真贵楷体",
            "书法/钟齐志莽行书",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Black",
            "阿里/数黑体/Alimama_ShuHeiTi_Bold",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Regular_Italic",
            "Noto_Sans_SC/NotoSansSC-Black",
            "黑体/Leefont蒙黑体",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Black",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Bold",
            "Noto_Sans_SC/NotoSansSC-Light",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_105_Heavy_105_Heavy",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Light",
            "书法/演示秋鸿楷",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Thin",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Bold_Italic",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Light",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_55_Regular_85_Bold",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Medium",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Thin",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Regular",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Light",
            "Emoji/NotoColorEmoji",
            "书法/仓耳周珂正大榜书",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Medium_Italic",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_35_Thin_35_Thin",
            "书法/鸿雷板书简体-Regular",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Regular",
            "黑体/千图厚黑体",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Black",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Bold_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Medium",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Light",
            "书法/庞门正道粗书体",
            "书法/钟齐流江毛草",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_115_Black_115_Black",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Bold",
            "黑体/标小智无界黑",
            "书法/演示夏行楷",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_45_Light_45_Light",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Medium",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Black",
            "黑体/Aa厚底黑",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Black_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Bold",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Light_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Light",
            "鸿蒙/HarmonyOS_Sans_Italic/HarmonyOS_Sans_Thin_Italic",
            "书法/演示佛系体",
            "Noto_Sans_SC/NotoSansSC-Regular",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Light",
            "鸿蒙/HarmonyOS_Sans/HarmonyOS_Sans_Medium",
            "书法/演示春风楷",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Thin",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Black_Italic",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Regular",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Medium",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Regular",
            "鸿蒙/HarmonyOS_Sans_TC/HarmonyOS_Sans_TC_Medium",
            "Noto_Sans_SC/NotoSansSC-Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_65_Medium_65_Medium",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_75_SemiBold_75_SemiBold",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Thin",
            "Noto_Sans_SC/NotoSansSC-Bold",
            "Noto_Sans_SC/NotoSansSC-Medium",
            "鸿蒙/HarmonyOS_Sans_SC/HarmonyOS_Sans_SC_Black",
            "书法/江西拙楷2.0",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Thin_Italic",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic_UI/HarmonyOS_Sans_Naskh_Arabic_UI_Bold",
            "阿里/钉钉进步体/DingTalk_JinBuTi_Regular",
            "书法/演示悠然小楷",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Thin",
            "阿里/普惠体/Alibaba_PuHuiTi_2.0_95_ExtraBold_95_ExtraBold",
            "鸿蒙/HarmonyOS_Sans_Naskh_Arabic/HarmonyOS_Sans_Naskh_Arabic_Black",
            "鸿蒙/HarmonyOS_Sans_Condensed_Italic/HarmonyOS_Sans_Condensed_Light_Italic",
            "鸿蒙/HarmonyOS_Sans_Condensed/HarmonyOS_Sans_Condensed_Bold"
        ]
        self.ui()


    def ui(self) :

        # 窗口尺寸及不可拉伸
        self.window_width = int(500*self.rate)
        self.window_height = int(370*self.rate)
        self.resize(self.window_width, self.window_height)
        self.setMinimumSize(QSize(self.window_width, self.window_height))
        self.setMaximumSize(QSize(self.window_width, self.window_height))
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint)

        # 窗口标题
        self.setWindowTitle("高级设置（关闭自动保存）")
        # 窗口图标
        self.setWindowIcon(ui.static.icon.APP_LOGO_ICON)
        # 鼠标样式
        self.setCursor(ui.static.icon.PIXMAP_CURSOR)
        # 设置字体
        self.setStyleSheet("font: 10pt '华康方圆体W7'; background: #FFFFFF;")

        # 顶部工具栏
        tab_widget = QTabWidget(self)
        tab_widget.setGeometry(QRect(0, 0, self.window_width, self.window_height))
        tab_widget.setTabPosition(QTabWidget.North)
        tab_widget.setStyleSheet("QTabBar:tab { min-height: %dpx; min-width: %dpx; background: rgba(255, 255, 255, 1);}"
                                 "QTabBar:tab:selected { background: rgba(62, 62, 62, 0.07); }"
                                 "QTabWidget::pane { border-image: none; }"
                                 "QLabel { background: transparent; }"
                                 "QPushButton { background: %s; border-radius: %spx; color: rgb(255, 255, 255); }"
                                 "QPushButton:hover { background-color: #83AAF9; }"
                                 "QPushButton:pressed { background-color: #4480F9; padding-left: 3px; padding-top: 3px; }"
                                 "QSlider { background: transparent; }"
                                 "QSlider:groove:horizontal { height: %spx;"
                                 "border-radius: %spx;"
                                 "margin-left: %spx;"
                                 "margin-right: %spx;"
                                 "background: rgba(89, 89, 89, 0.3); }"
                                 "QSlider:handle:horizontal { width: %spx;"
                                 "height: %spx;"
                                 "margin-top: %spx;"
                                 "margin-left: %spx;"
                                 "margin-bottom: %spx;"
                                 "margin-right: %spx;"
                                 "border-image: url(./config/icon/slider.png); }"
                                 "QSlider::sub-page:horizontal { height: %spx;"
                                 "border-radius: %spx;"
                                 "margin-left: %spx;"
                                 "background: %s; }"
                                 %(35*self.rate, 120*self.rate, self.color_2, 6.66*self.rate,
                                   8.66*self.rate, 4*self.rate, 13.33*self.rate, 13.33*self.rate,
                                   33.33*self.rate, 33.33*self.rate, -13.33*self.rate, -13.33*self.rate,
                                   -13.33*self.rate, -13.33*self.rate, 8.66*self.rate, 4*self.rate,
                                   10*self.rate, self.color_2))

        # 横向分割线
        label = QLabel(tab_widget)
        label.setGeometry(QRect(0, 35 * self.rate, self.window_width, 1))
        label.setFrameShadow(QFrame.Raised)
        label.setFrameShape(QFrame.Box)
        label.setStyleSheet("border-width: 1px; "
                            "border-style: solid; "
                            "border-color: rgba(62, 62, 62, 0.2);")

        # 样式设定页签
        font_tab = QWidget()
        tab_widget.addTab(font_tab, "")
        tab_widget.setTabText(tab_widget.indexOf(font_tab), "样式设定")
        tab_widget.setTabIcon(tab_widget.indexOf(font_tab), ui.static.icon.FONT_ICON)

        # 字体样式标签
        label = QLabel(font_tab)
        label.setText("字体样式: ")
        self.customSetGeometry(label, 20, 20, 500, 20)
        # 字体样式
        self.font_box = QComboBox(font_tab)
        self.customSetGeometry(self.font_box, 105, 20, 325, 25)
        self.font_box.setCursor(ui.static.icon.EDIT_CURSOR)
        self.font_box.setStyleSheet("QComboBox {background: rgba(255, 255, 255, 0.3); }"
                                    "QComboBox QAbstractItemView::item { min-height:40px; }")
        # 支持编辑和搜索
        self.font_box.setEditable(True)
        line_edit = QLineEdit()
        completer = self.font_box.completer()
        line_edit.setCompleter(completer)
        self.font_box.setItemDelegate(QStyledItemDelegate())
        utils.thread.createThread(self.createFontBox)
        # 字体样式?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", font_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 440, 20, 20, 20)
        button.clicked.connect(lambda: self.showDesc("font_type"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 字体色开关
        self.font_color_switch = ui.switch.SwitchOCR(font_tab, self.font_color_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.font_color_switch, 20, 70, 65, 20)
        self.font_color_switch.checkedChanged.connect(self.changeMangaFontColorSwitch)
        self.font_color_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 修改字体色
        self.font_color_button = QPushButton(qtawesome.icon("fa5s.paint-brush", color=self.font_color), "", font_tab)
        self.customSetGeometry(self.font_color_button, 100, 70, 80, 20)
        self.font_color_button.setCursor(ui.static.icon.EDIT_CURSOR)
        self.font_color_button.setText(" 字体色")
        self.font_color_button.clicked.connect(self.changeFontColor)
        self.font_color_button.setToolTip("<b>全局修改显示的字体颜色</b>")
        # 字体色?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", font_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 190, 70, 20, 20)
        button.clicked.connect(lambda: self.showDesc("font_color"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 字体轮廓色开关
        self.bg_color_switch = ui.switch.SwitchOCR(font_tab, self.bg_color_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.bg_color_switch, 270, 70, 65, 20)
        self.bg_color_switch.checkedChanged.connect(self.changeMangaBgColorUseSwitch)
        self.bg_color_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 修改字体轮廓色
        self.bg_color_button = QPushButton(qtawesome.icon("fa5s.paint-brush", color=self.bg_color), "", font_tab)
        self.customSetGeometry(self.bg_color_button, 350, 70, 80, 20)
        self.bg_color_button.setCursor(ui.static.icon.EDIT_CURSOR)
        self.bg_color_button.setText(" 轮廓色")
        self.bg_color_button.clicked.connect(self.changeBackgroundColor)
        self.bg_color_button.setToolTip("<b>全局修改显示的轮廓颜色</b>")
        # 字体轮廓色?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", font_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 440, 70, 20, 20)
        button.clicked.connect(lambda: self.showDesc("bg_color"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 字体大小开关
        self.font_size_switch = ui.switch.SwitchOCR(font_tab, self.font_size_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.font_size_switch, 20, 120, 65, 20)
        self.font_size_switch.checkedChanged.connect(self.changeFontSizeUseSwitch)
        self.font_size_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 字体大小数值设定
        self.font_size_spinbox = QSpinBox(font_tab)
        self.customSetGeometry(self.font_size_spinbox, 100, 120, 60, 20)
        self.font_size_spinbox.setMinimum(16)
        self.font_size_spinbox.setMaximum(512)
        self.font_size_spinbox.setValue(self.font_size)
        self.font_size_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        self.font_size_spinbox.valueChanged.connect(self.changeFontSize)
        self.font_size_spinbox.setStyleSheet("background: rgba(255, 255, 255, 0.3);")
        # 字体大小标签
        label = QLabel(font_tab)
        self.customSetGeometry(label, 175, 120, 100, 20)
        label.setText("字体大小")
        # 字体大小?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", font_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 240, 120, 20, 20)
        button.clicked.connect(lambda: self.showDesc("font_size"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 字体轮廓宽度设定
        self.shadow_size_spinbox = QDoubleSpinBox(font_tab)
        self.customSetGeometry(self.shadow_size_spinbox, 25, 170, 60, 20)
        self.shadow_size_spinbox.setDecimals(1)
        self.shadow_size_spinbox.setSingleStep(0.1)
        self.shadow_size_spinbox.setMinimum(0)
        self.shadow_size_spinbox.setMaximum(16)
        self.shadow_size_spinbox.setValue(self.shadow_size)
        self.shadow_size_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        self.shadow_size_spinbox.valueChanged.connect(self.changeShadowSize)
        self.shadow_size_spinbox.setStyleSheet("background: rgba(255, 255, 255, 0.3);")
        label = QLabel(font_tab)
        self.customSetGeometry(label, 100, 170, 100, 20)
        label.setText("字体轮廓宽度")
        # 字体轮廓宽度?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", font_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 195, 170, 20, 20)
        button.clicked.connect(lambda: self.showDesc("shadow_size"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 功能设定页签
        function_tab = QWidget()
        tab_widget.addTab(function_tab, "")
        tab_widget.setTabText(tab_widget.indexOf(function_tab), "功能设定")
        tab_widget.setTabIcon(tab_widget.indexOf(function_tab), ui.static.icon.FUNCTION_ICON)

        # 渲染缩放比例标签
        label = QLabel(function_tab)
        label.setText("渲染缩放比例: ")
        self.customSetGeometry(label, 20, 20, 500, 20)
        # 渲染缩放比例滑块
        self.detect_scale_slider = QSlider(function_tab)
        self.customSetGeometry(self.detect_scale_slider, 120, 20, 280, 25)
        self.detect_scale_slider.setRange(1, 4)
        self.detect_scale_slider.setSingleStep(1)
        self.detect_scale_slider.setOrientation(Qt.Horizontal)
        self.detect_scale_slider.setValue(self.detect_scale)
        self.detect_scale_slider.valueChanged.connect(self.changeDetectScale)
        self.detect_scale_slider.installEventFilter(self)
        self.detect_scale_slider.setCursor(ui.static.icon.SELECT_CURSOR)
        # 渲染缩放比例滑块数值标签
        self.detect_scale_slider_label = QLabel(function_tab)
        self.customSetGeometry(self.detect_scale_slider_label, 410, 20, 30, 20)
        self.detect_scale_slider_label.setText("x%s"%self.detect_scale)
        # 渲染缩放比例?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 440, 20, 20, 20)
        button.clicked.connect(lambda: self.showDesc("detect_scale"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent; }"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 字块合并间隔标签
        label = QLabel(function_tab)
        label.setText("字块合并间隔: ")
        self.customSetGeometry(label, 20, 70, 500, 20)
        # 字块合并间隔比例滑块
        self.merge_threshold_slider = QSlider(function_tab)
        self.customSetGeometry(self.merge_threshold_slider, 120, 70, 280, 25)
        self.merge_threshold_slider.setRange(1, 50)
        self.merge_threshold_slider.setSingleStep(1)
        self.merge_threshold_slider.setOrientation(Qt.Horizontal)
        self.merge_threshold_slider.setValue(self.merge_threshold*10)
        self.merge_threshold_slider.valueChanged.connect(self.changeMergeThreshold)
        self.merge_threshold_slider.installEventFilter(self)
        self.merge_threshold_slider.setCursor(ui.static.icon.SELECT_CURSOR)
        # 渲染缩放比例滑块数值标签
        self.merge_threshold_slider_label = QLabel(function_tab)
        self.customSetGeometry(self.merge_threshold_slider_label, 410, 70, 30, 20)
        self.merge_threshold_slider_label.setText("{:.1f}".format(self.merge_threshold))
        # 字块合并间隔?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 440, 70, 20, 20)
        button.clicked.connect(lambda: self.showDesc("merge_threshold"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent; }"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 过滤拟声词开关
        self.filtrate_switch = ui.switch.SwitchOCR(function_tab, self.filtrate_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.filtrate_switch, 20, 120, 65, 20)
        self.filtrate_switch.checkedChanged.connect(self.changeFiltrateUseSwitch)
        self.filtrate_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 过滤拟声词标签
        label = QLabel(function_tab)
        label.setText("过滤拟声词汇")
        self.customSetGeometry(label, 100, 120, 500, 20)
        # 过滤拟声词?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 190, 120, 20, 20)
        button.clicked.connect(lambda: self.showDesc("filtrate"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent; }"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 快速渲染开关
        self.fast_render_switch = ui.switch.SwitchOCR(function_tab, self.fast_render_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.fast_render_switch, 290, 120, 65, 20)
        self.fast_render_switch.checkedChanged.connect(self.changeFastRenderUseSwitch)
        self.fast_render_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 快速渲染标签
        label = QLabel(function_tab)
        label.setText("快速渲染")
        self.customSetGeometry(label, 370, 120, 500, 20)
        # 快速渲染?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 440, 120, 20, 20)
        button.clicked.connect(lambda: self.showDesc("fast_render"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # chatgpt延时开关
        self.chatgpt_delay_switch = ui.switch.SwitchOCR(function_tab, self.chatgpt_delay_use, startX=(65-20) * self.rate)
        self.customSetGeometry(self.chatgpt_delay_switch, 20, 170, 65, 20)
        self.chatgpt_delay_switch.checkedChanged.connect(self.changeChatgptDelayUseSwitch)
        self.chatgpt_delay_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # chatgpt延时时间设定
        self.chatgpt_delay_spinbox = QSpinBox(function_tab)
        self.customSetGeometry(self.chatgpt_delay_spinbox, 100, 170, 60, 20)
        self.chatgpt_delay_spinbox.setMinimum(1)
        self.chatgpt_delay_spinbox.setMaximum(180)
        self.chatgpt_delay_spinbox.setValue(self.chatgpt_delay_time)
        self.chatgpt_delay_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        self.chatgpt_delay_spinbox.valueChanged.connect(self.changeChatgptDelayTime)
        self.chatgpt_delay_spinbox.setStyleSheet("background: rgba(255, 255, 255, 0.3);")
        # chatgpt延时标签
        label = QLabel(function_tab)
        self.customSetGeometry(label, 175, 170, 200, 20)
        label.setText("ChatGPT翻译延时")
        # chatgpt延时?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 280, 170, 20, 20)
        button.clicked.connect(lambda: self.showDesc("chatgpt_delay"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 过滤短字符结果开关
        self.filter_char_switch = ui.switch.SwitchOCR(function_tab, self.filter_char_use, startX=(65-20)*self.rate)
        self.customSetGeometry(self.filter_char_switch, 20, 220, 65, 20)
        self.filter_char_switch.checkedChanged.connect(self.changeFilterCharUseSwitch)
        self.filter_char_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 过滤短字符结果长度设定
        self.filter_char_spinbox = QSpinBox(function_tab)
        self.customSetGeometry(self.filter_char_spinbox, 100, 220, 60, 20)
        self.filter_char_spinbox.setMinimum(1)
        self.filter_char_spinbox.setMaximum(5)
        self.filter_char_spinbox.setValue(self.filter_char_count)
        self.filter_char_spinbox.setCursor(ui.static.icon.SELECT_CURSOR)
        self.filter_char_spinbox.valueChanged.connect(self.changeFilterCharCount)
        self.filter_char_spinbox.setStyleSheet("background: rgba(255, 255, 255, 0.3);")
        # 过滤短字符结果标签
        label = QLabel(function_tab)
        self.customSetGeometry(label, 175, 220, 200, 20)
        label.setText("过滤短字符结果")
        # chatgpt延时?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", function_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 280, 220, 20, 20)
        button.clicked.connect(lambda: self.showDesc("filter_char"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 其他设定页签
        other_tab = QWidget()
        tab_widget.addTab(other_tab, "")
        tab_widget.setTabText(tab_widget.indexOf(other_tab), "其他设定")
        tab_widget.setTabIcon(tab_widget.indexOf(other_tab), ui.static.icon.OTHER_ICON)

        # 导出图片时重命名开关
        self.output_rename_switch = ui.switch.SwitchOCR(other_tab, self.output_rename_use, startX=(65-20) * self.rate)
        self.customSetGeometry(self.output_rename_switch, 20, 20, 65, 20)
        self.output_rename_switch.checkedChanged.connect(self.changeOutputRenameUseSwitch)
        self.output_rename_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 导出图片时重命名标签
        label = QLabel(other_tab)
        label.setText("导出时重命名")
        self.customSetGeometry(label, 100, 20, 500, 20)
        # 导出图片时重命名?号图标
        button = QPushButton(qtawesome.icon("fa.question-circle", color=self.color_2), "", other_tab)
        self.customSetIconSize(button, 20, 20)
        self.customSetGeometry(button, 190, 20, 20, 20)
        button.clicked.connect(lambda: self.showDesc("input_rename"))
        button.setCursor(ui.static.icon.QUESTION_CURSOR)
        button.setStyleSheet("QPushButton { background: transparent;}"
                             "QPushButton:hover { background-color: #83AAF9; }"
                             "QPushButton:pressed { background-color: #4480F9; padding-left: 3px;padding-top: 3px; }")

        # 自动打开图片翻译
        self.auto_open_manga_switch = ui.switch.SwitchOCR(other_tab, sign=self.auto_open_manga_use, startX=(65-20) * self.rate)
        self.customSetGeometry(self.auto_open_manga_switch, 20, 70, 65, 20)
        self.auto_open_manga_switch.checkedChanged.connect(self.changeAutoOpenMangaSwitch)
        self.auto_open_manga_switch.setCursor(ui.static.icon.SELECT_CURSOR)
        # 自动打开图片翻译标签
        label = QLabel(other_tab)
        self.customSetGeometry(label, 100, 70, 400, 20)
        label.setText("登录后自动打开图片翻译界面")

        # 加载背景图
        pixmap = ui.static.icon.MANGA_SETTING_PIXMAP.scaledToHeight(self.window_height)
        # 样式设定页面背景
        label = TransparentImageLabel(font_tab)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(QRect(0, 0, self.window_width, self.window_height))
        label.setPixmap(pixmap)
        label.lower()
        label.setOpacity(0.5)
        # 功能设定页面背景
        label = TransparentImageLabel(function_tab)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(QRect(0, 0, self.window_width, self.window_height))
        label.setPixmap(pixmap)
        label.lower()
        label.setOpacity(0.5)
        # 功能设定页面背景
        label = TransparentImageLabel(other_tab)
        label.setAlignment(Qt.AlignCenter)
        label.setGeometry(QRect(0, 0, self.window_width, self.window_height))
        label.setPixmap(pixmap)
        label.lower()
        label.setOpacity(0.5)


    # 根据分辨率定义控件位置尺寸
    def customSetGeometry(self, object, x, y, w, h) :

        object.setGeometry(QRect(int(x * self.rate),
                                 int(y * self.rate), int(w * self.rate),
                                 int(h * self.rate)))

    # 根据分辨率定义图标位置尺寸
    def customSetIconSize(self, object, w, h) :

        object.setIconSize(QSize(int(w * self.rate), int(h * self.rate)))


    # 改变自动打开图片翻译界面开关状态
    def changeAutoOpenMangaSwitch(self, checked) :

        if checked :
            self.auto_open_manga_use = True
        else:
            self.auto_open_manga_use = False
        self.object.yaml["auto_open_manga_use"] = self.auto_open_manga_use


    # 改变渲染缩放比例
    def changeDetectScale(self) :

        self.detect_scale = self.detect_scale_slider.value()
        self.object.config["mangaDetectScale"] = self.detect_scale
        self.detect_scale_slider_label.setText("x{}".format(self.detect_scale))


    # 改变字块合并间隔
    def changeMergeThreshold(self) :

        self.merge_threshold = round(self.merge_threshold_slider.value()/10, 1)
        self.object.config["mangaMergeThreshold"] = self.merge_threshold
        self.merge_threshold_slider_label.setText("{:.1f}".format(self.merge_threshold))


    # 说明窗口
    def showDesc(self, message_type) :

        self.desc_ui = ui.desc.Desc(self.object)
        # 文字缩放比例
        if message_type == "detect_scale" :
            self.desc_ui.setWindowTitle("文字缩放比例说明")
            self.desc_ui.desc_text.append("\n会对图片进行放大后再进行识别, 对于字体较小的图片可以调大此参数, 调大可能会增加文字识别耗时"
                                          "\n\n日文建议值为1, \n英文建议值为3")

        elif message_type == "font_color" :
            self.desc_ui.setWindowTitle("全局字体色说明")
            self.desc_ui.desc_text.append("\n开关开启, 会使所有图片, 翻译后渲染的文字使用此颜色"
                                          "\n开关关闭, 则由系统自动判断渲染颜色")

        elif message_type == "bg_color" :
            self.desc_ui.setWindowTitle("全局轮廓色说明")
            self.desc_ui.desc_text.append("\n开关开启, 会使所有图片, 翻译后渲染的文字轮廓使用此颜色"
                                          "\n开关关闭, 则由系统自动判断渲染颜色")

        elif message_type == "font_type" :
            self.desc_ui.setWindowTitle("全局字体样式说明")
            self.desc_ui.desc_text.append("\n使所有图片, 翻译后渲染的字体使用此样式"
                                          "\n\n默认值为 Noto_Sans_SC/NotoSansSC-Regular")

        elif message_type == "input_rename" :
            self.desc_ui.setWindowTitle("导出图片时重命名说明")
            self.desc_ui.desc_text.append("\n开关开启, 导出译图时会自动将所有图片, 按照图片列表框的序号重命名"
                                          "\n\n开关关闭, 则保留图片原名称")

        elif message_type == "fast_render" :
            self.desc_ui.setWindowTitle("快速渲染说明")
            self.desc_ui.desc_text.append("\n开关开启, 可以加快部分极端情况下的文字渲染速度"
                                          "\n\n但是大多数情况下会导致图片文字质量下降，请慎重启用")

        elif message_type == "shadow_size" :
            self.desc_ui.setWindowTitle("全局轮廓宽度说明")
            self.desc_ui.desc_text.append("\n影响文字渲染后的阴影轮廓宽度, 默认值为4.0")

        elif message_type == "filtrate" :
            self.desc_ui.setWindowTitle("过滤拟声词说明")
            self.desc_ui.desc_text.append("\n开启后, 不会识别和翻译拟声词, 默认值打开")

        elif message_type == "font_size" :
            self.desc_ui.setWindowTitle("字体大小说明")
            self.desc_ui.desc_text.append("\n开关开启, 会将所有图片渲染的文字大小按照此数值"
                                          "\n\n开关关闭, 则由系统自动判断渲染的文字大小"
                                          "\n\n范围为16-512, 单位pt"
                                          "\n\n默认值关闭")

        elif message_type == "merge_threshold" :
            self.desc_ui.setWindowTitle("字块合并间隔说明")
            self.desc_ui.desc_text.append("\n该数值影响文本框的合并情况, 数值越小, 文本框越不容易被合并"
                                          "\n\n建议值为5.0")

        elif message_type == "chatgpt_delay" :
            self.desc_ui.setWindowTitle("ChatGPT翻译延时说明")
            self.desc_ui.desc_text.append("\n考虑到部分用户ChatGPT账号有使用限制, 短时间内高频使用会出错, 此参数用于设置使用ChatGPT翻译时的延时"
                                          "\n\n开关开启时, 若当前使用的是ChatGPT翻译, 则两次翻译之间会经过所设置的数值大小的等待时间"
                                          "\n\n范围为1-180, 单位秒")

        elif message_type == "filter_char" :
            self.desc_ui.setWindowTitle("过滤短字符结果说明")
            self.desc_ui.desc_text.append("\n考虑到部分文字长度很短的句子很可能是误识别的情况, 此参数用于设置过滤短文字结果"
                                          "\n\n开关开启时, 若某个文本块的文字数小于所设置的数值, 则不会被翻译"
                                          "\n\n范围为1-5, 单位个")

        else :
            return

        self.desc_ui.show()


    # 改变全局字体色开关状态
    def changeMangaFontColorSwitch(self, checked) :

        self.object.config["mangaFontColorUse"] = checked


    # 改变全局轮廓色开关状态
    def changeMangaBgColorUseSwitch(self, checked) :

        self.object.config["mangaBgColorUse"] = checked


    # 修改字体颜色
    def changeFontColor(self) :

        self.hide()
        color = QColorDialog.getColor(QColor(self.font_color), None, "修改全局字体颜色")
        if color.isValid() :
            self.font_color = color.name()
            self.font_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=self.font_color))
            self.object.config["mangaFontColor"] = self.font_color
        self.show()


    # 修改轮廓颜色
    def changeBackgroundColor(self) :

        self.hide()
        color = QColorDialog.getColor(QColor(self.bg_color), None, "修改全局轮廓颜色")
        if color.isValid():
            self.bg_color = color.name()
            self.bg_color_button.setIcon(qtawesome.icon("fa5s.paint-brush", color=self.bg_color))
            self.object.config["mangaBgColor"] = self.bg_color
        self.show()


    # 全局字体样式下拉菜单
    def createFontBox(self) :

        sign, resp = translator.ocr.dango.mangaFontList(self.object)
        if sign :
            font_list = resp.get("available_fonts", [])
        else :
            font_list = copy.deepcopy(self.font_list)
        if not font_list :
            font_list = copy.deepcopy(self.font_list)

        for index, font in enumerate(font_list):
            self.font_box.addItem("")
            self.font_box.setItemText(index, font)
        self.font_box.setCurrentText(self.object.config["mangaFontType"])
        self.font_box.currentTextChanged.connect(self.changeMangaFontType)


    # 改变全局字体样式
    def changeMangaFontType(self) :

        self.object.config["mangaFontType"] = self.font_box.currentText()


    # 改变导出图片时重命名开关状态
    def changeOutputRenameUseSwitch(self, checked) :

        self.object.config["mangaOutputRenameUse"] = checked


    # 改变快速渲染开关状态
    def changeFastRenderUseSwitch(self, checked) :

        self.object.config["mangaFastRenderUse"] = checked


    # 改变全局轮廓宽度
    def changeShadowSize(self, value) :

        self.object.config["mangaShadowSize"] = value


    # 过滤拟声词开关状态
    def changeFiltrateUseSwitch(self, checked) :

        self.object.config["mangaFiltrateUse"] = checked

    # 改变字体大小开关状态
    def changeFontSizeUseSwitch(self, checked) :

        self.object.config["mangaFontSizeUse"] = checked


    # 改变字体大小
    def changeFontSize(self, value) :

        self.object.config["mangaFontSize"] = value


    # 改变chatgpt延时开关状态
    def changeChatgptDelayUseSwitch(self, checked) :

        self.object.config["mangaChatgptDelayUse"] = checked


    # 改变chatgpt延时时间
    def changeChatgptDelayTime(self, value) :

        self.object.config["mangaChatgptDelayTime"] = value


    # 改变过滤短字符开关状态
    def changeFilterCharUseSwitch(self, checked) :

        self.object.config["mangaFilterCharUse"] = checked


    # 改变过滤短字符长度
    def changeFilterCharCount(self, value) :

        self.object.config["mangaFilterCharCount"] = value


# 背景完全透明且不可被点击的按钮
class TransparentButton(QPushButton) :

    def __init__(self, parent=None) :

        super().__init__(parent)
        self.setFlat(True)
        self.setStyleSheet("QPushButton { background-color: transparent; border:none; }")


# 可绘制矩形框的QLabel
class CustomPaintLabel(QLabel) :

    paint_sign = pyqtSignal(int, int, int, int)
    paint_reset_sign = pyqtSignal(bool)
    paint_recover_sign = pyqtSignal(bool)

    def __init__(self, parent=None) :

        super().__init__(parent)
        self.paint_status = False
        self.is_drawing = False
        self.start_point = QPoint()
        self.end_point = QPoint()
        # ocr or recover
        self.paint_type = ""


    # 鼠标移动事件
    def mouseMoveEvent(self, e: QMouseEvent) :

        try :
            if not self.paint_status :
                return e.ignore()
            if self.is_drawing :
                self.end_point = e.pos()
                if self.end_point != self.start_point :
                    x, y, w, h = self.getRange()
                    self.paint_sign.emit(x, y, w, h)
        except :
            pass


    # 鼠标按下事件
    def mousePressEvent(self, e: QMouseEvent) :

        try :
            if not self.paint_status :
                return e.ignore()
            if e.button() == Qt.LeftButton :
                self.start_point = e.pos()
                self.end_point = self.start_point
                self.is_drawing = True
        except:
            pass


    # 鼠标松开事件
    def mouseReleaseEvent(self, e: QMouseEvent) :

        try :
            if not self.paint_status :
                return e.ignore()
            if e.button() == Qt.LeftButton :
                self.end_point = e.pos()
                if self.end_point != self.start_point :
                    if self.paint_type == "ocr" :
                        self.paint_reset_sign.emit(True)
                    elif self.paint_type == "recover" :
                        self.paint_recover_sign.emit(True)
                self.is_drawing = False
                self.start_point = QPoint()
                self.end_point = QPoint()
        except:
            pass


    # 获取鼠标起始点坐标
    def getRange(self) :

        x = self.start_point.x()
        if self.start_point.x() > self.end_point.x() :
            x = self.end_point.x()
        y = self.start_point.y()
        if self.start_point.y() > self.end_point.y() :
            y = self.end_point.y()
        w = abs(self.end_point.x() - self.start_point.x())
        h = abs(self.end_point.y() - self.start_point.y())

        return x, y, w, h


# 可以设置透明度的QLabel
class TransparentImageLabel(QLabel) :

    def __init__(self, parent=None) :
        super().__init__(parent)

    def setOpacity(self, opacity) :

        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(opacity)
        self.setGraphicsEffect(opacity_effect)


# 支持多选的列表框
class CustomListWidget(QListWidget) :

    def __init__(self, parent=None) :
        super().__init__(parent)
        self.setSelectionMode(QListWidget.MultiSelection)

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            self.setSelectionMode(QListWidget.ExtendedSelection)
        else:
            self.setSelectionMode(QListWidget.SingleSelection)
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        if event.modifiers() & (Qt.ControlModifier | Qt.ShiftModifier):
            self.setSelectionMode(QListWidget.ExtendedSelection)
        else:
            self.setSelectionMode(QListWidget.SingleSelection)
        super().mousePressEvent(event)
