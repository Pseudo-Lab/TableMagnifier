(function () {
  const TABLE_STYLE = {
    header: { fill: '#dbe4ee', text: '#0f172a', size: 13, weight: 700, align: 'center' },
    index: { fill: '#e8edf4', text: '#475569', size: 12, weight: 600, align: 'center' },
    row_label: { fill: '#f3f6fb', text: '#0f172a', size: 13, weight: 650, align: 'left' },
    body: { fill: '#ffffff', text: '#0f172a', size: 13, weight: 500, align: 'center' },
    numeric: { fill: '#ffffff', text: '#0f172a', size: 13, weight: 600, align: 'right', family: 'monospace' },
    muted: { fill: '#f8fafc', text: '#64748b', size: 12, weight: 500, align: 'center' },
    accent: { fill: '#ffffff', text: '#334155', size: 13, weight: 600, align: 'right', family: 'monospace' },
    highlight: { fill: '#eef4ff', text: '#0f172a', size: 13, weight: 700, align: 'right', family: 'monospace' },
    negative: { fill: '#fff7ed', text: '#b45309', size: 13, weight: 700, align: 'right', family: 'monospace' },
    total: { fill: '#dbe4ee', text: '#0f172a', size: 13, weight: 700, align: 'right', family: 'monospace' },
    total_label: { fill: '#dbe4ee', text: '#0f172a', size: 13, weight: 700, align: 'left' },
    note: { fill: '#f8fafc', text: '#475569', size: 13, weight: 500, align: 'left' },
  }

  const TEXT_STYLE = {
    body: { fill: '#ffffff', title: '#0f172a', text: '#475569' },
    note: { fill: '#f8fafc', title: '#0f172a', text: '#475569' },
    callout: { fill: '#eef3f8', title: '#0f172a', text: '#475569' },
  }

  const DEBUG_STYLE = {
    contentFrame: '#2563eb',
    titleBox: '#0f766e',
    metaBox: '#7c3aed',
    tableRect: '#dc2626',
    textRect: '#ea580c',
    regionRect: '#16a34a',
    overlayRect: '#db2777',
  }

  function font(weight, size, family) {
    const resolvedFamily = family === 'monospace' ? '"IBM Plex Mono", "SFMono-Regular", Consolas, monospace' : '"Inter", "Pretendard", "Noto Sans KR", sans-serif'
    return `${weight} ${size}px ${resolvedFamily}`
  }

  function cloneRect(rect) {
    return {
      x: Number(rect.x),
      y: Number(rect.y),
      width: Number(rect.width),
      height: Number(rect.height),
    }
  }

  function rectRight(rect) {
    return rect.x + rect.width
  }

  function rectBottom(rect) {
    return rect.y + rect.height
  }

  function mapRect(scene, rect) {
    const viewport = scene.viewport
    const surface = scene.surface
    const x = ((rect.x - viewport.x) / viewport.width) * surface.width
    const y = ((rect.y - viewport.y) / viewport.height) * surface.height
    const width = (rect.width / viewport.width) * surface.width
    const height = (rect.height / viewport.height) * surface.height
    return { x, y, width, height }
  }

  function measureTextWidth(ctx, text, options) {
    ctx.save()
    ctx.font = font(options.weight || 500, options.size || 13, options.family)
    const width = ctx.measureText(String(text)).width
    ctx.restore()
    return width
  }

  function measureTextBox(ctx, text, x, y, options) {
    const width = measureTextWidth(ctx, text, options)
    const height = options.lineHeight || options.size || 13
    return { x, y, width, height }
  }

  function wrapText(ctx, text, maxWidth, options) {
    ctx.save()
    ctx.font = font(options.weight || 500, options.size || 13, options.family)
    const words = String(text).split(/\s+/)
    const lines = []
    let current = ''
    for (const word of words) {
      const candidate = current ? `${current} ${word}` : word
      if (!current || ctx.measureText(candidate).width <= maxWidth) {
        current = candidate
      } else {
        lines.push(current)
        current = word
      }
    }
    if (current) {
      lines.push(current)
    }
    ctx.restore()
    return lines.length > 0 ? lines : [String(text)]
  }

  function overlapAmount(a, b) {
    const overlapX = Math.max(0, Math.min(rectRight(a), rectRight(b)) - Math.max(a.x, b.x))
    const overlapY = Math.max(0, Math.min(rectBottom(a), rectBottom(b)) - Math.max(a.y, b.y))
    return { overlapX, overlapY }
  }

  function rectInside(inner, outer, tolerance) {
    const slack = tolerance || 0
    return (
      inner.x >= outer.x - slack &&
      inner.y >= outer.y - slack &&
      rectRight(inner) <= rectRight(outer) + slack &&
      rectBottom(inner) <= rectBottom(outer) + slack
    )
  }

  function roundedRect(ctx, x, y, width, height, radius, fill, stroke) {
    ctx.beginPath()
    ctx.moveTo(x + radius, y)
    ctx.lineTo(x + width - radius, y)
    ctx.quadraticCurveTo(x + width, y, x + width, y + radius)
    ctx.lineTo(x + width, y + height - radius)
    ctx.quadraticCurveTo(x + width, y + height, x + width - radius, y + height)
    ctx.lineTo(x + radius, y + height)
    ctx.quadraticCurveTo(x, y + height, x, y + height - radius)
    ctx.lineTo(x, y + radius)
    ctx.quadraticCurveTo(x, y, x + radius, y)
    ctx.closePath()
    if (fill) {
      ctx.fillStyle = fill
      ctx.fill()
    }
    if (stroke) {
      ctx.strokeStyle = stroke
      ctx.stroke()
    }
  }

  function strokeDebugRect(ctx, rect, color, lineWidth, label) {
    ctx.save()
    ctx.strokeStyle = color
    ctx.lineWidth = lineWidth
    ctx.strokeRect(rect.x, rect.y, rect.width, rect.height)
    if (label) {
      ctx.fillStyle = color
      ctx.font = font(700, 11)
      ctx.textBaseline = 'top'
      ctx.fillText(label, rect.x + 4, Math.max(0, rect.y - 14))
    }
    ctx.restore()
  }

  function drawText(ctx, text, x, y, options) {
    ctx.save()
    ctx.font = font(options.weight || 500, options.size || 13, options.family)
    ctx.fillStyle = options.fill || '#0f172a'
    ctx.textBaseline = 'top'
    ctx.fillText(String(text), x, y)
    ctx.restore()
    return measureTextBox(ctx, text, x, y, options)
  }

  function drawTabs(ctx, scene) {
    const metrics = []
    let x = 78
    const y = 56
    scene.workbook.sheet_tabs.forEach((label, index) => {
      ctx.save()
      ctx.font = font(650, 13)
      const width = Math.max(72, Math.ceil(ctx.measureText(label).width) + 28)
      const rect = { x, y, width, height: 26 }
      roundedRect(ctx, rect.x, rect.y, rect.width, rect.height, 8, index === scene.workbook.active_sheet_index ? '#eef3f8' : '#f8fafc', '#dbe4ee')
      const textBox = drawText(ctx, label, x + 14, y + 6, { weight: 650, size: 13, fill: '#334155' })
      metrics.push({ index, label, active: index === scene.workbook.active_sheet_index, rect, textBox })
      x += width + 10
      ctx.restore()
    })
    return metrics
  }

  function drawTextBlock(ctx, scene, block) {
    const rect = mapRect(scene, block.rect)
    const style = TEXT_STYLE[block.style] || TEXT_STYLE.body
    const compactCallout = block.style === 'callout'
    const paddingX = compactCallout ? 16 : 18
    const paddingTop = compactCallout ? 6 : 12
    const paddingBottom = compactCallout ? 6 : 12
    const titleOptions = {
      weight: 700,
      size: compactCallout ? 12 : 15,
      fill: style.title,
      lineHeight: compactCallout ? 14 : 18,
    }
    const subtitleOptions = {
      size: compactCallout ? 10 : 11,
      fill: '#64748b',
      lineHeight: compactCallout ? 12 : 14,
    }
    const lineOptions = {
      size: compactCallout ? 11 : 12,
      fill: style.text,
      lineHeight: compactCallout ? 14 : 18,
    }
    const blockGap = compactCallout ? 2 : 6
    roundedRect(ctx, rect.x, rect.y, rect.width, rect.height, 12, style.fill, '#e2e8f0')
    const titleBox = drawText(ctx, block.title, rect.x + paddingX, rect.y + paddingTop, titleOptions)
    let y = rect.y + paddingTop + titleOptions.lineHeight + blockGap
    let subtitleBox = null
    if (block.metadata && block.metadata.subtitle) {
      subtitleBox = drawText(ctx, block.metadata.subtitle, rect.x + paddingX, y, subtitleOptions)
      y += subtitleOptions.lineHeight + blockGap
    }
    const lineBoxes = []
    const maxWidth = rect.width - paddingX * 2
    for (const line of block.lines || []) {
      const wrapped = wrapText(ctx, line, maxWidth, lineOptions)
      for (const part of wrapped) {
        lineBoxes.push(drawText(ctx, part, rect.x + paddingX, y, lineOptions))
        y += lineOptions.lineHeight
      }
    }
    const contentRect = {
      x: rect.x + paddingX,
      y: rect.y + paddingTop,
      width: rect.width - paddingX * 2,
      height: rect.height - paddingTop - paddingBottom,
    }
    return {
      id: block.element_id,
      type: block.type,
      rect,
      title: block.title,
      titleBox,
      subtitleBox,
      lineBoxes,
      contentRect,
      textBottom: lineBoxes.length > 0 ? rectBottom(lineBoxes[lineBoxes.length - 1]) : subtitleBox ? rectBottom(subtitleBox) : rectBottom(titleBox),
      overflowY: lineBoxes.length > 0 ? rectBottom(lineBoxes[lineBoxes.length - 1]) > rectBottom(contentRect) + 0.5 : false,
      padding: paddingX,
    }
  }

  function drawCellText(ctx, rect, cell, style) {
    if (!cell.text) return null
    ctx.save()
    ctx.font = font(style.weight, style.size, style.family)
    ctx.fillStyle = style.text
    ctx.textBaseline = 'middle'
    const textWidth = ctx.measureText(cell.text).width
    let x = rect.x + 12
    const align = cell.align || style.align
    if (align === 'center') {
      x = rect.x + (rect.width - textWidth) / 2
    } else if (align === 'right') {
      x = rect.x + rect.width - textWidth - 12
    }
    ctx.fillText(String(cell.text), x, rect.y + rect.height / 2)
    ctx.restore()
    const textRect = { x, y: rect.y + rect.height / 2 - (style.size || 13) / 2, width: textWidth, height: style.size || 13 }
    const paddingX = 10
    const paddingY = 0
    const contentRect = {
      x: rect.x + paddingX,
      y: rect.y + paddingY,
      width: Math.max(0, rect.width - paddingX * 2),
      height: Math.max(0, rect.height - paddingY * 2),
    }
    return {
      textRect,
      contentRect,
      overflowX: rectRight(textRect) > rectRight(contentRect) + 0.5 || textRect.x < contentRect.x - 0.5,
      overflowY: rectBottom(textRect) > rectBottom(contentRect) + 0.5 || textRect.y < contentRect.y - 0.5,
    }
  }

  function drawCellPattern(ctx, rect, pattern) {
    if (!pattern || pattern.kind !== 'diagonal_stripe') return false
    const inset = Number(pattern.inset ?? 6)
    const spacing = Math.max(Number(pattern.spacing ?? 12), 8)
    const strokeWidth = Number(pattern.stroke_width ?? 2.2)
    const opacity = Number(pattern.opacity ?? 0.55)

    ctx.save()
    ctx.beginPath()
    ctx.rect(rect.x + inset, rect.y + inset, Math.max(0, rect.width - inset * 2), Math.max(0, rect.height - inset * 2))
    ctx.clip()
    ctx.strokeStyle = String(pattern.color ?? '#2563eb')
    ctx.globalAlpha = opacity
    ctx.lineWidth = strokeWidth
    for (let offset = -rect.height; offset < rect.width + rect.height; offset += spacing) {
      ctx.beginPath()
      ctx.moveTo(rect.x + offset, rect.y + rect.height - inset)
      ctx.lineTo(rect.x + offset + rect.height, rect.y + inset)
      ctx.stroke()
    }
    ctx.restore()
    return true
  }

  function drawCellIcon(ctx, rect, icon) {
    if (!icon || icon.kind !== 'triangle') return false
    const anchor = String(icon.anchor ?? 'top_right')
    const size = Number(icon.size ?? 12)
    const inset = Number(icon.inset ?? 7)
    let points

    if (anchor === 'top_left') {
      points = [
        [rect.x + inset, rect.y + inset],
        [rect.x + inset + size, rect.y + inset],
        [rect.x + inset, rect.y + inset + size],
      ]
    } else if (anchor === 'bottom_left') {
      points = [
        [rect.x + inset, rect.y + rect.height - inset],
        [rect.x + inset + size, rect.y + rect.height - inset],
        [rect.x + inset, rect.y + rect.height - inset - size],
      ]
    } else if (anchor === 'bottom_right') {
      points = [
        [rect.x + rect.width - inset, rect.y + rect.height - inset],
        [rect.x + rect.width - inset - size, rect.y + rect.height - inset],
        [rect.x + rect.width - inset, rect.y + rect.height - inset - size],
      ]
    } else {
      points = [
        [rect.x + rect.width - inset, rect.y + inset],
        [rect.x + rect.width - inset - size, rect.y + inset],
        [rect.x + rect.width - inset, rect.y + inset + size],
      ]
    }

    ctx.save()
    ctx.beginPath()
    ctx.moveTo(points[0][0], points[0][1])
    ctx.lineTo(points[1][0], points[1][1])
    ctx.lineTo(points[2][0], points[2][1])
    ctx.closePath()
    ctx.fillStyle = String(icon.color ?? '#2563eb')
    ctx.globalAlpha = Number(icon.opacity ?? 0.92)
    ctx.fill()
    ctx.restore()
    return true
  }

  function drawCellFrame(ctx, rect, frame) {
    if (!frame) return false
    const inset = Number(frame.inset ?? 4)
    const strokeWidth = Number(frame.stroke_width ?? 2.2)

    ctx.save()
    ctx.strokeStyle = String(frame.color ?? '#2563eb')
    ctx.lineWidth = strokeWidth
    ctx.strokeRect(rect.x + inset, rect.y + inset, Math.max(0, rect.width - inset * 2), Math.max(0, rect.height - inset * 2))
    ctx.restore()
    return true
  }

  function drawCellMetadata(ctx, rect, cell) {
    const metadata = cell.metadata || {}
    let markerCount = 0
    if (drawCellPattern(ctx, rect, metadata.pattern)) markerCount += 1
    if (drawCellIcon(ctx, rect, metadata.icon)) markerCount += 1
    if (drawCellFrame(ctx, rect, metadata.frame)) markerCount += 1
    return markerCount
  }

  function drawTable(ctx, scene, table) {
    const rect = mapRect(scene, table.rect)
    const titleOptions = { weight: 700, size: 16, fill: '#0f172a', lineHeight: 18 }
    const subtitleOptions = { size: 11, fill: '#64748b', lineHeight: 14 }
    roundedRect(ctx, rect.x, rect.y, rect.width, rect.height, 14, '#ffffff', '#dbe4ee')
    const titleBox = drawText(ctx, table.title || '', rect.x, rect.y - 44, titleOptions)
    let subtitleBox = null
    if (table.metadata && table.metadata.subtitle) {
      subtitleBox = drawText(ctx, table.metadata.subtitle, rect.x, rect.y - 22, subtitleOptions)
    }

    const colOffsets = [0]
    table.column_widths.forEach((width) => colOffsets.push(colOffsets[colOffsets.length - 1] + width))
    const rowOffsets = [0]
    table.row_heights.forEach((height) => rowOffsets.push(rowOffsets[rowOffsets.length - 1] + height))

    const cellTextMetrics = []
    let markerCount = 0
    for (const cell of table.cells) {
      const cellX = table.rect.x + colOffsets[cell.col]
      const cellY = table.rect.y + rowOffsets[cell.row]
      const cellWidth = table.column_widths.slice(cell.col, cell.col + (cell.col_span || 1)).reduce((sum, value) => sum + value, 0)
      const cellHeight = table.row_heights.slice(cell.row, cell.row + (cell.row_span || 1)).reduce((sum, value) => sum + value, 0)
      const mappedCellRect = mapRect(scene, { x: cellX, y: cellY, width: cellWidth, height: cellHeight })
      const style = TABLE_STYLE[cell.style] || TABLE_STYLE.body
      ctx.fillStyle = style.fill
      ctx.fillRect(mappedCellRect.x, mappedCellRect.y, mappedCellRect.width, mappedCellRect.height)
      ctx.strokeStyle = '#dbe4ee'
      ctx.strokeRect(mappedCellRect.x, mappedCellRect.y, mappedCellRect.width, mappedCellRect.height)
      markerCount += drawCellMetadata(ctx, mappedCellRect, cell)
      const textMetrics = drawCellText(ctx, mappedCellRect, cell, style)
      if (textMetrics) {
        cellTextMetrics.push({
          row: cell.row,
          col: cell.col,
          text: String(cell.text),
          textRect: textMetrics.textRect,
          contentRect: textMetrics.contentRect,
          overflowX: textMetrics.overflowX,
          overflowY: textMetrics.overflowY,
        })
      }
    }

    return {
      id: table.element_id,
      type: table.type,
      rect,
      title: table.title || '',
      titleBox,
      subtitleBox,
      lastRowBottom: rectBottom(rect),
      overflowY: rectBottom(rect) > scene.surface.height - 80,
      cellTextMetrics,
      cellOverflowCount: cellTextMetrics.filter((metric) => metric.overflowX || metric.overflowY).length,
      markerCount,
    }
  }

  function drawOverlayNote(ctx, scene, note) {
    if (!note) return null
    const box = { x: scene.surface.width - 420, y: 118, width: 372, height: 162 }
    const titleOptions = { weight: 700, size: 16, fill: '#0f172a', lineHeight: 18 }
    const lineOptions = { size: 12, fill: '#475569', lineHeight: 18 }
    roundedRect(ctx, box.x, box.y, box.width, box.height, 14, '#f8fafc', '#cbd5e1')
    const titleBox = drawText(ctx, note.title, box.x + 18, box.y + 16, titleOptions)
    let y = box.y + 48
    const maxWidth = box.width - 36
    const lineBoxes = []
    for (const line of wrapText(ctx, note.text, maxWidth, lineOptions)) {
      lineBoxes.push(drawText(ctx, line, box.x + 18, y, lineOptions))
      y += 18
    }
    return {
      id: note.id,
      type: 'overlay_note',
      rect: box,
      title: note.title,
      titleBox,
      lineBoxes,
      textBottom: lineBoxes.length > 0 ? rectBottom(lineBoxes[lineBoxes.length - 1]) : rectBottom(titleBox),
      overflowY: lineBoxes.length > 0 ? rectBottom(lineBoxes[lineBoxes.length - 1]) > box.y + box.height - 18 + 0.5 : false,
      padding: 18,
    }
  }

  function drawDebugOverlay(ctx, metrics) {
    strokeDebugRect(ctx, metrics.contentFrame, DEBUG_STYLE.contentFrame, 2, 'content')
    strokeDebugRect(ctx, metrics.pageTitleBox, DEBUG_STYLE.titleBox, 1.5, 'page-title')
    strokeDebugRect(ctx, metrics.pageMetaBox, DEBUG_STYLE.metaBox, 1.5, 'page-meta')
    for (const tab of metrics.tabs) {
      strokeDebugRect(ctx, tab.rect, '#94a3b8', 1)
    }
    for (const element of metrics.elements) {
      const color = element.type === 'table' ? DEBUG_STYLE.tableRect : DEBUG_STYLE.textRect
      strokeDebugRect(ctx, element.rect, color, 2, element.id)
      if (element.titleBox) {
        strokeDebugRect(ctx, element.titleBox, DEBUG_STYLE.titleBox, 1)
      }
      if (element.subtitleBox) {
        strokeDebugRect(ctx, element.subtitleBox, DEBUG_STYLE.metaBox, 1)
      }
    }
    for (const region of metrics.regions) {
      strokeDebugRect(ctx, region.rect, DEBUG_STYLE.regionRect, 1, region.label)
    }
    if (metrics.overlayNote) {
      strokeDebugRect(ctx, metrics.overlayNote.rect, DEBUG_STYLE.overlayRect, 2, metrics.overlayNote.id)
    }
  }

  function renderWorkbookSceneToCanvas(canvas, scene, options) {
    if (!canvas || !scene) return
    const opts = options || {}
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.round(scene.surface.width * dpr)
    canvas.height = Math.round(scene.surface.height * dpr)
    canvas.style.width = `${scene.surface.width}px`
    canvas.style.maxWidth = '100%'
    canvas.style.height = 'auto'
    const ctx = canvas.getContext('2d')
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    const contentFrame = {
      x: 40,
      y: 42,
      width: scene.surface.width - 80,
      height: scene.surface.height - 66,
    }

    ctx.clearRect(0, 0, scene.surface.width, scene.surface.height)
    ctx.fillStyle = '#f8fafc'
    ctx.fillRect(0, 0, scene.surface.width, scene.surface.height)
    roundedRect(ctx, 18, 18, scene.surface.width - 36, scene.surface.height - 36, 18, '#ffffff', '#dbe4ee')
    roundedRect(ctx, contentFrame.x, contentFrame.y, contentFrame.width, contentFrame.height, 16, '#ffffff', '#e2e8f0')

    const tabs = drawTabs(ctx, scene)
    const pageTitleBox = drawText(ctx, scene.page.title, 76, 92, { weight: 700, size: 18, fill: '#0f172a', lineHeight: 20 })
    const pageMetaText = `${scene.page.sheet_tab_label} · 페이지 ${scene.page.page_index + 1}/1`
    const pageMetaBox = drawText(ctx, pageMetaText, 76, 120, { size: 11, fill: '#64748b', lineHeight: 14 })

    const elementMetrics = []
    for (const element of scene.page.elements) {
      if (element.type === 'table') {
        elementMetrics.push(drawTable(ctx, scene, element))
      } else if (element.type === 'text_block') {
        elementMetrics.push(drawTextBlock(ctx, scene, element))
      }
    }

    const overlayNote = drawOverlayNote(ctx, scene, scene.overlay_note)

    if (scene.selected_region_id) {
      const region = (scene.page.regions || []).find((item) => item.public_id === scene.selected_region_id)
      if (region) {
        const rect = mapRect(scene, region.rect)
        ctx.save()
        ctx.strokeStyle = '#2563eb'
        ctx.lineWidth = 2
        roundedRect(ctx, rect.x, rect.y, rect.width, rect.height, 12, null, '#2563eb')
        ctx.restore()
      }
    }

    const mappedRegions = (scene.page.regions || []).map((region) => ({
      publicId: region.public_id,
      role: region.role,
      label: region.label,
      rect: mapRect(scene, region.rect),
    }))

    const layoutErrors = []
    function pushLayoutError(code, message, extra) {
      layoutErrors.push({ code, message, ...extra })
    }

    for (const element of elementMetrics) {
      if (element.titleBox && !rectInside(element.titleBox, contentFrame, 0.5)) {
        pushLayoutError('title_outside_content_frame', 'Element title spills outside the workbook content frame.', {
          elementId: element.id,
        })
      }
      if (element.subtitleBox && !rectInside(element.subtitleBox, contentFrame, 0.5)) {
        pushLayoutError('subtitle_outside_content_frame', 'Element subtitle spills outside the workbook content frame.', {
          elementId: element.id,
        })
      }
      if (element.overflowY) {
        pushLayoutError('element_overflow_y', 'Element content exceeds the allowed vertical bounds.', {
          elementId: element.id,
        })
      }
      if (element.contentRect && element.titleBox && !rectInside(element.titleBox, element.contentRect, 0.5)) {
        pushLayoutError('text_block_title_overflow', 'Text block title does not fit inside its content box.', {
          elementId: element.id,
        })
      }
      if (element.contentRect && element.subtitleBox && !rectInside(element.subtitleBox, element.contentRect, 0.5)) {
        pushLayoutError('text_block_subtitle_overflow', 'Text block subtitle does not fit inside its content box.', {
          elementId: element.id,
        })
      }
      if (Array.isArray(element.lineBoxes) && element.contentRect) {
        for (const lineBox of element.lineBoxes) {
          if (!rectInside(lineBox, element.contentRect, 0.5)) {
            pushLayoutError('text_block_line_overflow', 'Wrapped text line spills outside its content box.', {
              elementId: element.id,
            })
          }
        }
      }
      if (element.type === 'table') {
        if (element.titleBox && element.subtitleBox && rectBottom(element.titleBox) + 4 > element.subtitleBox.y + 0.5) {
          pushLayoutError('table_heading_overlap', 'Table title and subtitle overlap.', { elementId: element.id })
        }
        if (element.subtitleBox && rectBottom(element.subtitleBox) + 8 > element.rect.y + 0.5) {
          pushLayoutError('table_subtitle_body_overlap', 'Table subtitle overlaps the table body.', { elementId: element.id })
        }
        if (!element.subtitleBox && element.titleBox && rectBottom(element.titleBox) + 8 > element.rect.y + 0.5) {
          pushLayoutError('table_title_body_overlap', 'Table title overlaps the table body.', { elementId: element.id })
        }
        for (const metric of element.cellTextMetrics || []) {
          if (metric.overflowX || metric.overflowY) {
            pushLayoutError('table_cell_text_overflow', 'Table cell text does not fit inside its padded content box.', {
              elementId: element.id,
              cellKey: `${metric.row}:${metric.col}`,
            })
          }
        }
      }
    }

    if (overlayNote) {
      if (!rectInside(overlayNote.rect, contentFrame, 0.5)) {
        pushLayoutError('overlay_note_outside_content_frame', 'Overlay note spills outside the workbook content frame.', {
          elementId: overlayNote.id,
        })
      }
      if (overlayNote.titleBox && !rectInside(overlayNote.titleBox, overlayNote.rect, 18.5)) {
        pushLayoutError('overlay_note_title_overflow', 'Overlay note title does not fit inside its padded content box.', {
          elementId: overlayNote.id,
        })
      }
      if (Array.isArray(overlayNote.lineBoxes)) {
        const overlayContentRect = {
          x: overlayNote.rect.x + 18,
          y: overlayNote.rect.y + 16,
          width: overlayNote.rect.width - 36,
          height: overlayNote.rect.height - 34,
        }
        for (const lineBox of overlayNote.lineBoxes) {
          if (!rectInside(lineBox, overlayContentRect, 0.5)) {
            pushLayoutError('overlay_note_line_overflow', 'Overlay note text spills outside its content box.', {
              elementId: overlayNote.id,
            })
          }
        }
      }
      if (overlayNote.overflowY) {
        pushLayoutError('overlay_note_overflow_y', 'Overlay note exceeds its vertical bounds.', {
          elementId: overlayNote.id,
        })
      }
    }

    for (const tableElement of elementMetrics.filter((element) => element.type === 'table')) {
      const headingBoxes = [tableElement.titleBox, tableElement.subtitleBox].filter(Boolean)
      if (headingBoxes.length === 0) continue
      for (const otherElement of elementMetrics) {
        if (otherElement.id === tableElement.id) continue
        for (const headingBox of headingBoxes) {
          const overlap = overlapAmount(otherElement.rect, headingBox)
          if (overlap.overlapX > 0.5 && overlap.overlapY > 0.5) {
            pushLayoutError('table_heading_element_overlap', 'Another element overlaps a table heading block.', {
              elementId: tableElement.id,
              overlappingElementId: otherElement.id,
              overlapX: overlap.overlapX,
              overlapY: overlap.overlapY,
            })
          }
        }
      }
    }

    const debugMetrics = {
      surfaceId: opts.surfaceId || null,
      canvasSize: { width: scene.surface.width, height: scene.surface.height },
      contentFrame,
      pageTitleBox,
      pageMetaBox,
      tabs,
      elements: elementMetrics,
      regions: mappedRegions,
      overlayNote,
      invalidLayout: layoutErrors.length > 0,
      layoutErrors,
      consoleErrors: Array.isArray(opts.consoleErrors) ? opts.consoleErrors.slice() : [],
    }

    if (opts.debug) {
      drawDebugOverlay(ctx, debugMetrics)
    }

    globalThis.__TABLE_ENV_DEBUG__ = debugMetrics
    canvas.dataset.surfaceId = opts.surfaceId || ''
    canvas.dataset.debug = opts.debug ? '1' : '0'
  }

  globalThis.TableEnvCanvas = {
    renderWorkbookSceneToCanvas,
  }
})()
