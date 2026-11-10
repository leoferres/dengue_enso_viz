"""Render the frozen v2 data, then make the 30 fps LinkedIn copy."""
import argparse
import csv
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "enso_dengue_mpl"))
os.environ.setdefault("CPL_LOG", os.devnull)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
from qgis.core import (Qgis, QgsApplication, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsDateTimeRange, QgsLayoutExporter, QgsLayoutItemLabel, QgsLayoutItemMap, QgsLayoutItemPicture,
    QgsLayoutItemShape, QgsLayoutMeasurement, QgsLayoutPoint, QgsLayoutSize, QgsPrintLayout,
    QgsProject, QgsRectangle, QgsFillSymbol, QgsTextFormat, QgsRuleBasedRenderer, QgsProperty,
    QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from qgis.PyQt.QtCore import QDate, QDateTime, QLocale, QRectF, Qt, QTime
from qgis.PyQt.QtGui import QColor, QFont, QFontDatabase

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "animation.qgz"
NAME = "enso_dengue_2007_2025_v2_linkedin_30fps"


FPS = 3
DPI = 150
PAGE_W, PAGE_H = 256.0, 144.0
MAP = (4.0, 4.0, 120.0, 136.0)
CHART = (130.0, 66.0, 122.0, 64.0)
AX_L, AX_R = 0.10, 0.985
AX_B, AX_T = 0.14, 0.92
EXTENT = (-82.4, -4.5, -66.5, 13.7)
FONT = "Noto Sans"
SEA = "#dfeef7"
YEARS = range(2007, 2026)
L_OE = "Casos observados / esperados del mes — mpio"
L_CAB = "Casos del mes (círculos)"
L_ONI = "ONI del mes (3 meses antes) y fase"
L_LIM = "Límites departamentales"
L_CTRY = "Países vecinos (Natural Earth 10m)"
OE_TEXT = {   # rule label of the map layer -> plain-language legend text
    "≥ 4×": "≥ 4×   cuatro veces o más lo esperado",
    "2 – 4×": "2–4×   entre el doble y el cuádruple",
    "1.25 – 2×": "1.25–2×   algo más de lo esperado",
    "0.8 – 1.25×": "0.8–1.25×   lo esperado",
    "0.5 – 0.8×": "0.5–0.8×   algo menos",
    "< 0.5×": "< 0.5×   menos de la mitad",
    "Pocos casos esperados": "gris: se esperaban menos de 2 casos",
}

CIRCLES = [100, 1000, 5000]
OUTLINE = "154,154,154,110"
MES = "format_date(coalesce(@map_start_time, to_datetime('2016-01-01T00:00:00')), 'yyyyMM')"
MES_DATE = "coalesce(@map_start_time, to_datetime('2016-01-01T00:00:00'))"
ONI_FILL = (f"with_variable('o', attribute(@feature, 'oni_' || {MES}), "
            f"with_variable('f', attribute(@feature, 'fase_' || {MES}), CASE "
            "WHEN @f = 'El Niño' THEN ramp_color('Reds', scale_linear(@o, 0.5, 2.6, 0.25, 0.75)) "
            "WHEN @f = 'La Niña' THEN ramp_color('Blues', scale_linear(-@o, 0.5, 2.0, 0.25, 0.75)) "
            "ELSE '#e0e0e0' END))")
SEASON_ES = {"DJF": "dic–feb", "JFM": "ene–mar", "FMA": "feb–abr", "MAM": "mar–may", "AMJ": "abr–jun",
             "MJJ": "may–jul", "JJA": "jun–ago", "JAS": "jul–sep", "ASO": "ago–oct", "SON": "sep–nov",
             "OND": "oct–dic", "NDJ": "nov–ene"}
def fill(color, outline=OUTLINE, width=0.05):
    return QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width),
                                       "outline_width_unit": "MM"})

def ruled(rules, parent_filter=None):
    """rules: list of (label, filter expression, symbol)."""
    root = QgsRuleBasedRenderer.Rule(None)
    base = root
    if parent_filter:
        base = QgsRuleBasedRenderer.Rule(None, filterExp=parent_filter)
        root.appendChild(base)
    for label, expr, sym in rules:
        base.appendChild(QgsRuleBasedRenderer.Rule(sym, filterExp=expr, label=label))
    return QgsRuleBasedRenderer(root)

def r_oni_badge():
    """The badge is drawn by the label (its background, constant size on screen); the polygon only anchors it."""
    return ruled([("Recuadro: mes del mapa y temperatura del Pacífico ecuatorial 3 meses antes, °C sobre lo normal "
                   "(rojo El Niño, azul La Niña, gris neutro)", "",
                   fill("0,0,0,0", "0,0,0,0", 0))])

def label_oni_badge(lyr):
    from qgis.core import QgsTextBackgroundSettings
    from qgis.PyQt.QtCore import QSizeF
    s = QgsPalLayerSettings()
    s.isExpression = True
    # e.g. "Enero 2016 / Pacífico sep–nov / +2.3 °C · El Niño" (Oceanic Niño Index of the season centred 3 months before)
    seasons = "map(" + ", ".join(f"'{k}', '{v}'" for k, v in SEASON_ES.items()) + ")"
    s.fieldName = (f"with_variable('o', attribute(@feature, 'oni_' || {MES}), "
                   f"title(format_date({MES_DATE}, 'MMMM yyyy', 'es')) || '\\n' || 'Pacífico ' || "
                   f"map_get({seasons}, left(attribute(@feature, 'est_' || {MES}), 3)) || '\\n' || "
                   f"if(@o > 0, '+', '') || format_number(@o, 1) || ' °C · ' || attribute(@feature, 'fase_' || {MES}))")
    tf = QgsTextFormat()
    tf.setFont(QFont("Noto Sans", 9, QFont.Bold))
    tf.setSize(8.5)
    tf.setColor(QColor("#111111"))
    bg = QgsTextBackgroundSettings()
    bg.setEnabled(True)
    bg.setType(QgsTextBackgroundSettings.ShapeRectangle)
    bg.setSizeType(QgsTextBackgroundSettings.SizeBuffer)
    bg.setSize(QSizeF(2.0, 1.4))
    bg.setSizeUnit(Qgis.RenderUnit.Millimeters)
    bg.setRadii(QSizeF(1.2, 1.2))
    bg.setFillColor(QColor("#e0e0e0"))
    bg.setStrokeColor(QColor("#3d3d3d"))
    bg.setStrokeWidth(0.3)
    tf.setBackground(bg)
    s.setFormat(tf)
    prop = getattr(QgsPalLayerSettings, "Property", QgsPalLayerSettings)
    s.dataDefinedProperties().setProperty(prop.ShapeFillColor, QgsProperty.fromExpression(ONI_FILL))
    s.placement = Qgis.LabelPlacement.OverPoint
    s.multilineAlign = Qgis.LabelMultiLineAlignment.Center
    s.obstacleSettings().setIsObstacle(False)
    s.priority = 10
    s.displayAll = True
    lyr.setLabeling(QgsVectorLayerSimpleLabeling(s))
    lyr.setLabelsEnabled(True)

def tf(size, bold=False, color="#222222"):
    t = QgsTextFormat()
    f = QFont(FONT)
    f.setBold(bold)
    t.setFont(f)
    t.setSize(size)
    t.setSizeUnit(Qgis.RenderUnit.Points)
    t.setColor(QColor(color))
    return t

def label(layout, text, x, y, w, h, size, bold=False, color="#222222"):
    lab = QgsLayoutItemLabel(layout)
    lab.setText(text)
    lab.setTextFormat(tf(size, bold, color))
    lab.setMode(QgsLayoutItemLabel.ModeFont)
    layout.addLayoutItem(lab)
    lab.attemptMove(QgsLayoutPoint(x, y))
    lab.attemptResize(QgsLayoutSize(w, h))
    return lab

def chart_png(path, oni, fase, cases):
    """ONI (lagged 3 months, coloured by phase) above national monthly cases; axes span AX_L..AX_R of the width."""
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": [FONT, "DejaVu Sans"], "font.size": 7,
                         "axes.unicode_minus": False})          # Noto Sans has no U+2212 in matplotlib
    w, h = CHART[2] / 25.4, CHART[3] / 25.4
    fig = plt.figure(figsize=(w, h), dpi=300)
    n = len(oni)
    x = np.arange(n) + 0.5
    col = ["#d6604d" if p == "El Niño" else "#4393c3" if p == "La Niña" else "#bdbdbd" for p in fase]
    a1 = fig.add_axes([AX_L, 0.56, AX_R - AX_L, AX_T - 0.56])
    a1.bar(x, oni, width=1.0, color=col, linewidth=0)
    a1.axhline(0, color="#555555", lw=0.4)
    a1.set_xlim(0, n)
    a1.set_ylabel("°C", fontsize=6.5)
    a1.set_title("Pacífico ecuatorial 3 meses antes, °C sobre lo normal (rojo: El Niño; azul: La Niña)",
                 loc="left", fontsize=7, pad=2)
    a1.set_xticks([])
    a2 = fig.add_axes([AX_L, AX_B, AX_R - AX_L, 0.47 - AX_B])
    a2.fill_between(x, cases / 1000, color="#3d3d3d", lw=0, alpha=0.85, step="mid")
    a2.set_xlim(0, n)
    a2.set_ylim(0, cases.max() / 1000 * 1.05)
    a2.set_ylabel("miles", fontsize=6.5)
    a2.set_title("Casos de dengue por mes en toda Colombia", loc="left", fontsize=7, pad=2)
    ticks = [12 * (y - 2007) for y in YEARS if (y - 2007) % 3 == 0]
    a2.set_xticks(ticks)
    a2.set_xticklabels([str(2007 + t // 12) for t in ticks])
    for a in (a1, a2):
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.tick_params(length=2, width=0.4, labelsize=6.5)
        for s in ("left", "bottom"):
            a.spines[s].set_linewidth(0.4)
    fig.savefig(path, dpi=300, facecolor="white")
    plt.close(fig)

def circle_mm(v):
    """Circle diameter in mm; matches the saved map style."""
    return 0.5 + (16 - 0.5) * (v / 6000) ** 0.5

def shape(layout, kind, x, y, w, h, color, outline="#9a9a9a", width=0.15):
    sh = QgsLayoutItemShape(layout)
    sh.setShapeType(kind)
    sh.setSymbol(QgsFillSymbol.createSimple({"color": color, "outline_color": outline, "outline_width": str(width)}))
    layout.addLayoutItem(sh)
    sh.attemptMove(QgsLayoutPoint(x, y))
    sh.attemptResize(QgsLayoutSize(w, h))
    return sh

def legend_colors(layout, layers, x, y):
    """Colour key of the municipal map, high to low, colours read from the layer's own rules."""
    rules = {r.label(): r.symbol().color() for r in layers[L_OE].renderer().rootRule().children()}
    assert set(rules) == set(OE_TEXT), sorted(rules)
    label(layout, "Color: casos del mes ÷ casos esperados", x, y, 72, 5, 7.5, True)
    for i, key in enumerate(OE_TEXT):
        c = rules[key]
        yy = y + 5.5 + i * 3.7
        shape(layout, QgsLayoutItemShape.Rectangle, x, yy, 5.5, 2.8, f"{c.red()},{c.green()},{c.blue()},255")
        label(layout, OE_TEXT[key], x + 7, yy - 0.6, 66, 4, 7)

def legend_circles(layout, x, y):
    """Circle-size key: the same diameters (mm) as on the map."""
    label(layout, "Círculos: casos del mes", x, y, 48, 5, 7.5, True)
    base = y + 6 + circle_mm(CIRCLES[-1])          # circles sit on a common baseline
    cx = x + 1
    for v in CIRCLES:
        d = circle_mm(v)
        shape(layout, QgsLayoutItemShape.Ellipse, cx, base - d, d, d, "61,61,61,179", "255,255,255,230", 0.2)
        label(layout, f"{v:,}".replace(",", " "), cx + d / 2 - 6, base + 1, 12, 4, 7).setHAlign(Qt.AlignHCenter)
        cx += d + 5
    label(layout, "El mayor: Cali, 5 866 casos (mayo 2024)", x, base + 5.5, 48, 4, 6.5, color="#555555")

def build_layout(project, layers, chart_path):
    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.pageCollection().page(0).setPageSize(QgsLayoutSize(PAGE_W, PAGE_H))

    m = QgsLayoutItemMap(layout)
    m.attemptSetSceneRect(QRectF(*MAP))
    m.setCrs(QgsCoordinateReferenceSystem("EPSG:9377"))
    m.setLayers([layers[n] for n in (L_ONI, L_CAB, L_LIM, L_OE, L_CTRY)])
    m.setKeepLayerSet(True)
    m.setBackgroundColor(QColor(SEA))
    m.setFrameEnabled(True)
    m.setFrameStrokeColor(QColor("#9a9a9a"))
    m.setFrameStrokeWidth(QgsLayoutMeasurement(0.2))
    m.setIsTemporal(True)
    layout.addLayoutItem(m)
    tr = QgsCoordinateTransform(QgsCoordinateReferenceSystem("EPSG:4326"), m.crs(), project)
    m.zoomToExtent(tr.transformBoundingBox(QgsRectangle(*EXTENT)))

    x0 = MAP[0] + MAP[2] + 6
    label(layout, "Dengue y El Niño / La Niña en Colombia, 2007–2025", x0, 5, 122, 8, 12, True)
    label(layout, "Color de cada municipio: sus casos del mes frente a los esperados, es decir, los de ese mismo mes "
                  "(enero, febrero…) en un año típico de 2007–2025, ajustados a su población y a las semanas del mes. Rojo: más casos de lo "
                  "normal; azul: menos. Recuadro en el Pacífico: cuánto más caliente (+) o más fría (−) que lo normal estuvo "
                  "el agua del Pacífico ecuatorial unos 3 meses antes, en promedio de los 3 meses indicados (°C). "
                  "Rojo: El Niño; azul: La Niña.",
          x0, 14, 121, 18, 7, color="#444444")
    legend_colors(layout, layers, x0, 34)
    legend_circles(layout, x0 + 74, 34)

    pic = QgsLayoutItemPicture(layout)
    pic.setPicturePath(str(chart_path))
    pic.setResizeMode(QgsLayoutItemPicture.Stretch)
    layout.addLayoutItem(pic)
    pic.attemptMove(QgsLayoutPoint(CHART[0], CHART[1]))
    pic.attemptResize(QgsLayoutSize(CHART[2], CHART[3]))

    marker = QgsLayoutItemShape(layout)
    marker.setShapeType(QgsLayoutItemShape.Rectangle)
    marker.setSymbol(QgsFillSymbol.createSimple({"color": "255,140,0,110", "outline_color": "#e65100",
                                                 "outline_width": "0.25"}))
    layout.addLayoutItem(marker)

    label(layout, "Barra naranja: el mes que muestra el mapa. Fuentes: casos de dengue y dengue grave notificados al "
                  "Sistema Nacional de Vigilancia en Salud Pública (Instituto Nacional de Salud), por semana de inicio "
                  "de síntomas y municipio donde ocurrió el contagio; población del Departamento Administrativo Nacional de Estadística; temperatura "
                  "del Pacífico: Índice Oceánico de El Niño, Administración Nacional Oceánica y Atmosférica de EE. UU.",
          x0, 129.5, 122, 11, 6, color="#666666")
    return layout, m, marker

def series(months):
    with (ROOT / "timeline.csv").open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["month"] for r in rows] == months
    return (np.array([float(r["oni_lag3"]) for r in rows]),
            [r["phase"] for r in rows], np.array([float(r["cases"]) for r in rows]))


def sha256(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "output", help="Output directory")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / (NAME + ".mp4")
    if output.exists():
        parser.error(f"Already exists: {output}")
    QLocale.setDefault(QLocale(QLocale.English, QLocale.UnitedKingdom))
    QgsApplication.setPrefixPath(os.environ.get("QGIS_PREFIX_PATH", "/usr"), True)
    app = QgsApplication([], False)
    app.initQgis()
    for font in sorted((ROOT / "fonts").glob("*.ttf")):
        assert QFontDatabase.addApplicationFont(str(font)) >= 0, font
        font_manager.fontManager.addfont(str(font))
    project = QgsProject.instance()
    assert project.read(str(PROJECT)), PROJECT
    layers = {l.name(): l for l in project.mapLayers().values()}
    assert set(layers) == {L_OE, L_CAB, L_ONI, L_LIM, L_CTRY}
    assert all(l.isValid() for l in layers.values())
    layers[L_ONI].setRenderer(r_oni_badge())
    label_oni_badge(layers[L_ONI])
    months = [f"{y}{m:02d}" for y in YEARS for m in range(1, 13)]
    oni, phase, cases = series(months)
    with tempfile.TemporaryDirectory(prefix="enso_render_") as directory:
        tmp = Path(directory)
        chart = tmp / "chart.png"
        chart_png(chart, oni, phase, cases)
        layout, m, marker = build_layout(project, layers, chart)
        cw = CHART[2] * (AX_R - AX_L) / len(months)
        settings = QgsLayoutExporter.ImageExportSettings()
        settings.dpi = DPI
        settings.exportMetadata = False
        layout.setCustomProperty("exportWorldFile", False)
        for i, ym in enumerate(months):
            start = QDate(int(ym[:4]), int(ym[4:]), 1)
            m.setTemporalRange(QgsDateTimeRange(QDateTime(start, QTime(0, 0)), QDateTime(start.addMonths(1), QTime(0, 0))))
            marker.attemptMove(QgsLayoutPoint(CHART[0] + CHART[2] * AX_L + i * cw, CHART[1] + CHART[3] * (1 - AX_T)))
            marker.attemptResize(QgsLayoutSize(max(cw, 0.6), CHART[3] * (AX_T - AX_B)))
            result = QgsLayoutExporter(layout).exportToImage(str(tmp / f"f{i:04d}.png"), settings)
            assert result == QgsLayoutExporter.Success, (ym, result)
            if i % 24 == 0:
                print("frame", i, ym, flush=True)
        del layout
        project.clear()
        app.exitQgis()
        intermediate = tmp / "v2_3fps.mp4"
        subprocess.run(["ffmpeg", "-n", "-loglevel", "error", "-framerate", str(FPS), "-i", str(tmp / "f%04d.png"),
                        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                        "-crf", "20", "-movflags", "+faststart", str(intermediate)], check=True)
        subprocess.run(["ffmpeg", "-n", "-hide_banner", "-loglevel", "error", "-i", str(intermediate),
                        "-map", "0:v:0", "-vf", "fps=30", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
                        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output)], check=True)
    reference = ROOT / "reference.mp4"
    print(f"Wrote {output} (1510 × 850, 30 fps, 76 seconds)")
    print("SHA-256:", sha256(output))
    print("Matches reference:", sha256(output) == sha256(reference))


if __name__ == "__main__":
    main()

