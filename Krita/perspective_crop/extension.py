import sys
from krita import *
from PyQt5.QtWidgets import QWidget, QMessageBox, QApplication, QAction
from PyQt5.QtGui import QPainter, QPen, QColor, QImage, QTransform, QPolygonF, QIcon, QCursor
from PyQt5.QtCore import Qt, QPointF, QRect

class PerspectiveOverlay(QWidget):
    def __init__(self, parent=None):
        super(PerspectiveOverlay, self).__init__(parent)
        # Make the window frameless, translucent, and cover the screen
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setCursor(Qt.CrossCursor)
        self.setMouseTracking(True)

        self.points = []

        # Cover the geometry of the active Krita window
        main_window = Krita.instance().activeWindow().qwindow()
        self.setGeometry(main_window.geometry())

        self.show()
        self.setFocus()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(event.pos())
            self.update()

            if len(self.points) == 4:
                # Slight delay to let the user see the 4th point
                QApplication.processEvents()
                self.process_transform()
                self.close()

        elif event.button() == Qt.RightButton:
            self.close() # Cancel

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Background dimming
        painter.fillRect(self.rect(), QColor(0, 0, 0, 50))

        if not self.points:
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(self.rect().center(), "Click Top-Left Corner")
            return

        # Draw Lines
        pen = QPen(QColor(0, 255, 255), 2, Qt.SolidLine)
        painter.setPen(pen)

        for i in range(len(self.points) - 1):
            painter.drawLine(self.points[i], self.points[i+1])

        # Draw dynamic line to mouse
        if len(self.points) < 4:
            mouse_pos = self.mapFromGlobal(QCursor.pos())
            painter.drawLine(self.points[-1], mouse_pos)
        else:
            # Close the loop
            painter.drawLine(self.points[3], self.points[0])

        # Draw Points
        painter.setBrush(QColor(255, 255, 0))
        for i, p in enumerate(self.points):
            painter.drawEllipse(p, 5, 5)

    def process_transform(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            return

        # --- IMPORTANT COORDINATE NOTE ---
        # The Python API for Krita does not easily give us "Canvas Pan/Zoom".
        # We assume the user has fit the image to the screen or is at 100%.
        # For this V1 plugin, we capture the SCREEN pixels of the canvas area.
        # This creates a "What You See Is What You Get" crop.

        # 1. Grab Screen Geometry
        screen = QApplication.primaryScreen()
        # We take a screenshot of the area defined by our overlay
        # This bypasses the complex zoom math, but limits resolution to your monitor.
        pixmap = screen.grabWindow(0, self.x(), self.y(), self.width(), self.height())
        qimg = pixmap.toImage()

        # 2. Sort Points (Top-Left, TR, BR, BL) to ensure correct orientation
        # A simple sort by Y then X usually works for standard crops
        # but let's trust user input order: TL -> TR -> BR -> BL
        pts = self.points

        # 3. Calculate Dimensions
        def dist(p1, p2):
            return ((p1.x() - p2.x())**2 + (p1.y() - p2.y())**2)**0.5

        width_top = dist(pts[0], pts[1])
        width_bot = dist(pts[3], pts[2])
        height_left = dist(pts[0], pts[3])
        height_right = dist(pts[1], pts[2])

        target_w = int(max(width_top, width_bot))
        target_h = int(max(height_left, height_right))

        # 4. Transform
        src_quad = QPolygonF([QPointF(p) for p in pts])
        dst_quad = QPolygonF([
            QPointF(0, 0),
            QPointF(target_w, 0),
            QPointF(target_w, target_h),
            QPointF(0, target_h)
        ])

        transform = QTransform()
        transform, valid = QTransform.quadToQuad(src_quad, dst_quad)

        if valid:
            new_img = qimg.transformed(transform, Qt.SmoothTransformation)
            final_img = new_img.copy(0, 0, target_w, target_h)

            # 5. Create New Krita Document
            new_doc = Krita.instance().createDocument(target_w, target_h, "Perspective Crop", "RGBA", "U8", "", 300.0)

            # Convert QImage to bytes
            final_img = final_img.convertToFormat(QImage.Format_RGBA8888)
            ptr = final_img.bits()
            ptr.setsize(final_img.byteCount())

            new_doc.pixelData(0, 0, target_w, target_h, ptr.asstring())
            Krita.instance().activeWindow().addView(new_doc)


class PerspectiveCropExtension(Extension):
    def __init__(self, parent):
        super(PerspectiveCropExtension, self).__init__(parent)

    def setup(self):
        pass

    def createActions(self, window):
        action = window.createAction("perspective_crop_trigger", "Perspective Crop Tool", "tools/scripts")
        action.setToolTip("Click 4 corners to crop and fix perspective.")

        # Load Icon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), "icons", "perspective_crop.svg")
        action.setIcon(QIcon(icon_path))

        action.triggered.connect(self.launch_tool)

    def launch_tool(self):
        doc = Krita.instance().activeDocument()
        if not doc:
            QMessageBox.warning(None, "Error", "Please open a document first.")
            return

        # Warning about zoom limitation
        # msg = QMessageBox()
        # msg.setText("Note: Because this tool captures the screen, ensure your image fits on screen or is zoomed as desired.")
        # msg.exec_()

        self.overlay = PerspectiveOverlay()
