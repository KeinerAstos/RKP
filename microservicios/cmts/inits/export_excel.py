"""Excel nativo para el ciclo actual. Solo biblioteca estándar; no modifica CSV."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from xml.sax.saxutils import escape
import re
from zipfile import ZipFile, ZIP_DEFLATED
from tempfile import TemporaryFile
import shutil

S = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
BOGOTA = timezone(timedelta(hours=-5))
HEADERS = ['CMTS', 'IP', 'Fecha Colombia', 'Total INIT', 'Gravedad', 'Consulta', 'Variación INIT', 'Detalle']
MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'

def clean(value):
    return escape(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', str(value or ''))[:32767])

def cell(ref, value, style=0, formula=False):
    if value is None:
        return f'<c r="{ref}" s="{style}"/>'
    if formula:
        return f'<c r="{ref}" s="{style}"><f>{escape(value)}</f><v>0</v></c>'
    if isinstance(value, (int, float)):
        return f'<c r="{ref}" s="{style}"><v>{value}</v></c>'
    return f'<c r="{ref}" s="{style}" t="inlineStr"><is><t xml:space="preserve">{clean(value)}</t></is></c>'

def date_number(value):
    stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if stamp.tzinfo is None: stamp = stamp.replace(tzinfo=timezone.utc)
    local = stamp.astimezone(BOGOTA).replace(tzinfo=None)
    return (local - datetime(1899, 12, 30)).total_seconds() / 86400

def select_rows(rows, search='', estado='', sort='total_init', direction=-1):
    allowed = {'cmts', 'fecha', 'total_init', 'estado', 'variacion'}
    if sort not in allowed: sort = 'total_init'
    selected = [dict(r) for r in rows if search.strip().casefold() in (str(r['cmts'])+' '+str(r['ip'])).casefold() and (not estado or (not r['ok'] or r['total_init'] is None if estado=='error' else r['estado']==estado))]
    missing = [r for r in selected if r.get(sort) is None]
    existing = [r for r in selected if r.get(sort) is not None]
    existing.sort(key=lambda r: r[sort], reverse=direction < 0)
    return existing + missing

def write_excel(path: Path, rows, *, search='', estado='', include_chart=True, historical=False, period=None):
    with TemporaryFile() as row_file:
        _write_excel(path, rows, row_file, search=search, estado=estado, include_chart=include_chart, historical=historical, period=period)

def _write_excel(path, rows, row_file, *, search, estado, include_chart, historical, period):
    rows = list(rows) if include_chart else rows
    if include_chart and len(rows)>10000: raise ValueError('Excel del ciclo actual admite hasta 10000 CMTS')
    count = 0
    for n,r in enumerate(rows,9):
        count += 1
        if n > 1048576: raise ValueError('El histórico supera el límite de filas de Excel; reduce los filtros')
        valid=bool(r['ok']) and r['total_init'] is not None
        values=[r['cmts'],r['ip'],date_number(r['fecha']),r['total_init'] if valid else None,r['estado'],'ÉXITO' if valid else 'FALLÓ',r.get('variacion'),r.get('error') or '']
        xml=f'<row r="{n}" ht="30" customHeight="1">'+''.join(cell(chr(65+i)+str(n),v,5 if i==2 else (4 if i in (3,6) else (6 if i==7 else 0))) for i,v in enumerate(values))+'</row>'
        row_file.write(xml.encode('utf-8'))
    end = max(9, 8+count)
    title = 'CMTS · Histórico de 5 días' if historical else 'CMTS · Monitoreo INIT'
    count_label = 'Lecturas visibles' if historical else 'CMTS visibles'
    init_label = 'INIT de lecturas visibles' if historical else 'INIT visibles'
    note = 'Histórico: cada fila es una lectura. INIT suma lecturas visibles; no es el estado actual de la red.' if historical else 'Filtra la tabla: resumen y gráfica usan las filas visibles. Lecturas fallidas = INIT vacío.'
    if period:
        note += ' Rango Colombia: ' + ' a '.join(t.astimezone(BOGOTA).strftime('%d/%m/%Y %H:%M') for t in period)
    body = [f'<row r="1" ht="32" customHeight="1">{cell("A1", title, 1)}</row>',
        f'<row r="3" ht="40" customHeight="1">{cell("A3", count_label, 2)}{cell("B3", f"SUBTOTAL(103,A9:A{end})", 4, True)}{cell("C3", init_label, 2)}{cell("D3", f"SUBTOTAL(109,D9:D{end})", 4, True)}{cell("E3", "Lecturas válidas", 2)}{cell("F3", f"SUBTOTAL(102,D9:D{end})", 4, True)}</row>',
        f'<row r="4" ht="24" customHeight="1">{cell("A4", "Exportado: "+datetime.now(BOGOTA).strftime("%d/%m/%Y %H:%M:%S")+" · Colombia", 2)}</row>',
        f'<row r="5" ht="24" customHeight="1">{cell("A5", "Búsqueda: "+(search or "Todos")+" · Resultado: "+(estado or "Todos"), 2)}</row>',
        f'<row r="6" ht="24" customHeight="1">{cell("A6", note, 2)}</row>',
        '<row r="8" ht="28" customHeight="1">'+''.join(cell(chr(65+i)+'8', h, 3) for i,h in enumerate(HEADERS))+'</row>']
    if not count: row_file.write(('<row r="9">'+''.join(cell(c+'9',None) for c in 'ABCDEFGH')+'</row>').encode('utf-8'))
    drawing = '<drawing r:id="rId2"/>' if include_chart and count else ''
    sheet=f'''<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="{S}" xmlns:r="{R}"><dimension ref="A1:H{end}"/><sheetViews><sheetView workbookViewId="0" showGridLines="0"><pane xSplit="1" ySplit="8" topLeftCell="B9" activePane="bottomRight" state="frozen"/></sheetView></sheetViews><sheetFormatPr defaultRowHeight="22"/><cols><col min="1" max="1" width="38" customWidth="1"/><col min="2" max="2" width="18" customWidth="1"/><col min="3" max="3" width="23" customWidth="1"/><col min="4" max="4" width="14" customWidth="1"/><col min="5" max="5" width="23" customWidth="1"/><col min="6" max="6" width="16" customWidth="1"/><col min="7" max="7" width="18" customWidth="1"/><col min="8" max="8" width="65" customWidth="1"/></cols><sheetData>{''.join(body)}__DATA_ROWS__</sheetData><mergeCells count="4"><mergeCell ref="A1:H1"/><mergeCell ref="A4:H4"/><mergeCell ref="A5:H5"/><mergeCell ref="A6:H6"/></mergeCells><conditionalFormatting sqref="D9:D{end}"><colorScaleUnused/></conditionalFormatting>{drawing}<tableParts count="1"><tablePart r:id="rId1"/></tableParts></worksheet>'''
    # Native three-color scale; empty failed readings remain empty.
    sheet=sheet.replace('<colorScaleUnused/>','<cfRule type="colorScale" priority="1"><colorScale><cfvo type="min"/><cfvo type="percentile" val="50"/><cfvo type="max"/><color rgb="FFE2F0D9"/><color rgb="FFFFE699"/><color rgb="FFF8CBAD"/></colorScale></cfRule>')
    styles=f'''<styleSheet xmlns="{S}"><numFmts count="2"><numFmt numFmtId="164" formatCode="dd/mm/yyyy hh:mm:ss"/><numFmt numFmtId="165" formatCode="+#,##0;-#,##0;0"/></numFmts><fonts count="3"><font><sz val="11"/><name val="Calibri"/><color rgb="FF243746"/></font><font><b/><sz val="20"/><name val="Calibri"/><color rgb="FF123A55"/></font><font><b/><sz val="11"/><name val="Calibri"/><color rgb="FFFFFFFF"/></font></fonts><fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF123A55"/><bgColor indexed="64"/></patternFill></fill></fills><borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders><cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs><cellXfs count="7"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center"/></xf><xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="2" fillId="2" borderId="0" xfId="0"><alignment vertical="center"/></xf><xf numFmtId="3" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"><alignment horizontal="right" vertical="center"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"><alignment vertical="center"/></xf></cellXfs><cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles><dxfs count="0"/><tableStyles count="0" defaultTableStyle="TableStyleMedium2" defaultPivotStyle="PivotStyleLight16"/></styleSheet>'''
    table=f'<table xmlns="{S}" id="1" name="TablaCMTS" displayName="TablaCMTS" ref="A8:H{end}" totalsRowShown="0"><autoFilter ref="A8:H{end}"/><tableColumns count="8">'+''.join(f'<tableColumn id="{i}" name="{clean(h)}"/>' for i,h in enumerate(HEADERS,1))+'</tableColumns><tableStyleInfo name="TableStyleMedium2" showFirstColumn="0" showLastColumn="0" showRowStripes="1" showColumnStripes="0"/></table>'
    relns='http://schemas.openxmlformats.org/package/2006/relationships'
    parts={
      '_rels/.rels':f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{R}/officeDocument" Target="xl/workbook.xml"/></Relationships>',
      'xl/workbook.xml':f'<workbook xmlns="{S}" xmlns:r="{R}"><bookViews><workbookView/></bookViews><sheets><sheet name="CMTS INIT" sheetId="1" r:id="rId1"/></sheets><calcPr calcId="191029" fullCalcOnLoad="1" forceFullCalc="1"/></workbook>',
      'xl/_rels/workbook.xml.rels':f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{R}/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="{R}/styles" Target="styles.xml"/></Relationships>',
      'xl/worksheets/sheet1.xml':sheet,
      'xl/worksheets/_rels/sheet1.xml.rels':f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{R}/table" Target="../tables/table1.xml"/>'+ (f'<Relationship Id="rId2" Type="{R}/drawing" Target="../drawings/drawing1.xml"/>' if include_chart and count else '')+'</Relationships>',
      'xl/styles.xml':styles,'xl/tables/table1.xml':table,
    }
    if include_chart and count:
        cats=''.join(f'<c:pt idx="{i}"><c:v>{clean(r["cmts"])}</c:v></c:pt>' for i,r in enumerate(rows))
        nums=''.join(f'<c:pt idx="{i}"><c:v>{int(r["total_init"])}</c:v></c:pt>' for i,r in enumerate(rows) if r['ok'] and r['total_init'] is not None)
        parts['xl/charts/chart1.xml']=f'''<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><c:lang val="es-CO"/><c:chart><c:title><c:tx><c:rich><a:bodyPr/><a:lstStyle/><a:p><a:r><a:rPr lang="es-CO" sz="1600"/><a:t>INIT por CMTS · filas visibles</a:t></a:r></a:p></c:rich></c:tx></c:title><c:plotArea><c:layout/><c:barChart><c:barDir val="bar"/><c:grouping val="clustered"/><c:ser><c:idx val="0"/><c:order val="0"/><c:tx><c:v>Total INIT</c:v></c:tx><c:spPr><a:solidFill><a:srgbClr val="0876CE"/></a:solidFill></c:spPr><c:cat><c:strRef><c:f>'CMTS INIT'!$A$9:$A${end}</c:f><c:strCache><c:ptCount val="{len(rows)}"/>{cats}</c:strCache></c:strRef></c:cat><c:val><c:numRef><c:f>'CMTS INIT'!$D$9:$D${end}</c:f><c:numCache><c:formatCode>#,##0</c:formatCode><c:ptCount val="{len(rows)}"/>{nums}</c:numCache></c:numRef></c:val></c:ser><c:gapWidth val="50"/><c:axId val="100"/><c:axId val="200"/></c:barChart><c:catAx><c:axId val="100"/><c:scaling><c:orientation val="maxMin"/></c:scaling><c:axPos val="l"/><c:tickLblPos val="nextTo"/><c:crossAx val="200"/><c:crosses val="autoZero"/><c:auto val="1"/><c:lblAlgn val="ctr"/><c:lblOffset val="100"/></c:catAx><c:valAx><c:axId val="200"/><c:scaling><c:orientation val="minMax"/><c:min val="0"/></c:scaling><c:axPos val="b"/><c:majorGridlines/><c:numFmt formatCode="#,##0" sourceLinked="0"/><c:tickLblPos val="nextTo"/><c:crossAx val="100"/><c:crosses val="autoZero"/><c:crossBetween val="between"/></c:valAx></c:plotArea><c:plotVisOnly val="1"/><c:dispBlanksAs val="gap"/><c:showDLblsOverMax val="0"/></c:chart></c:chartSpace>'''
        parts['xl/drawings/drawing1.xml']=f'''<xdr:wsDr xmlns:xdr="http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><xdr:oneCellAnchor><xdr:from><xdr:col>9</xdr:col><xdr:colOff>0</xdr:colOff><xdr:row>0</xdr:row><xdr:rowOff>0</xdr:rowOff></xdr:from><xdr:ext cx="9144000" cy="6096000"/><xdr:graphicFrame macro=""><xdr:nvGraphicFramePr><xdr:cNvPr id="2" name="INIT por CMTS"/><xdr:cNvGraphicFramePr/></xdr:nvGraphicFramePr><xdr:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/></xdr:xfrm><a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/chart"><c:chart xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" xmlns:r="{R}" r:id="rId1"/></a:graphicData></a:graphic></xdr:graphicFrame><xdr:clientData/></xdr:oneCellAnchor></xdr:wsDr>'''
        parts['xl/drawings/_rels/drawing1.xml.rels']=f'<Relationships xmlns="{relns}"><Relationship Id="rId1" Type="{R}/chart" Target="../charts/chart1.xml"/></Relationships>'
    overrides={'/xl/workbook.xml':'spreadsheetml.sheet.main','/xl/worksheets/sheet1.xml':'spreadsheetml.worksheet','/xl/styles.xml':'spreadsheetml.styles','/xl/tables/table1.xml':'spreadsheetml.table'}
    types=''.join(f'<Override PartName="{p}" ContentType="application/vnd.openxmlformats-officedocument.{t}+xml"/>' for p,t in overrides.items())
    if include_chart and count: types+='<Override PartName="/xl/drawings/drawing1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawing+xml"/><Override PartName="/xl/charts/chart1.xml" ContentType="application/vnd.openxmlformats-officedocument.drawingml.chart+xml"/>'
    parts['[Content_Types].xml']='<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/>'+types+'</Types>'
    with ZipFile(path,'w',ZIP_DEFLATED) as z:
        for name,content in parts.items():
            if name == 'xl/worksheets/sheet1.xml':
                prefix, suffix = content.split('__DATA_ROWS__')
                with z.open(name, 'w') as dest:
                    dest.write(prefix.encode('utf-8')); row_file.seek(0)
                    shutil.copyfileobj(row_file, dest, length=65536)
                    dest.write(suffix.encode('utf-8'))
            else: z.writestr(name,content.encode('utf-8'))
