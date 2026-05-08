<script lang="ts">
  type Props = {
    content: string;
    onSkuClick?: (sku: string) => void;
    onOrderClick?: (orderId: string) => void;
    onCustomerClick?: (customerId: string) => void;
  };

  type UuidKind = "order" | "customer";

  type TextSegment = {
    text: string;
    bold?: boolean;
    sku?: string;
    uuid?: string;
    uuidKind?: UuidKind;
  };

  type ParagraphBlock = {
    type: "paragraph";
    lines: TextSegment[][];
  };

  type ListBlock = {
    type: "list";
    items: TextSegment[][];
  };

  type TableBlock = {
    type: "table";
    headers: TextSegment[][];
    rows: TableCell[][];
  };

  type TableCell = {
    segments: TextSegment[];
    orderId?: string;
    customerId?: string;
  };

  type CodeBlock = {
    type: "code";
    text: string;
  };

  type MarkdownBlock = ParagraphBlock | ListBlock | TableBlock | CodeBlock;

  let { content, onSkuClick, onOrderClick, onCustomerClick }: Props = $props();

  const blocks = $derived(parseMarkdown(content));

  function labelKind(label: string): UuidKind | undefined {
    const normalizedLabel = label.toLowerCase().replace(/[^a-z]/g, "");
    if (normalizedLabel.includes("customer")) return "customer";
    if (normalizedLabel.includes("order")) return "order";
    return undefined;
  }

  function segmentText(segments: TextSegment[]) {
    return segments.map((segment) => segment.text).join("");
  }

  function plainSegmentText(segments: TextSegment[]) {
    return segmentText(segments);
  }

  function appendTokenSegments(
    segments: TextSegment[],
    text: string,
    bold = false,
  ) {
    const normalizedText = text
      .replace(/[\u200b-\u200f\ufeff]/g, "")
      .replace(/[\u2010-\u2015\u2212]/g, "-");
    const tokenPattern =
      /\b([A-Z]{3}-\d{4})\b|([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/gi;
    let cursor = 0;

    for (const match of normalizedText.matchAll(tokenPattern)) {
      const index = match.index ?? 0;
      if (index > cursor) {
        segments.push({ text: normalizedText.slice(cursor, index), bold });
      }
      if (match[1]) {
        segments.push({
          text: match[1].toUpperCase(),
          sku: match[1].toUpperCase(),
          bold,
        });
      }
      if (match[2]) {
        segments.push({ text: match[2], uuid: match[2], bold });
      }
      cursor = index + match[0].length;
    }

    if (cursor < normalizedText.length) {
      segments.push({ text: normalizedText.slice(cursor), bold });
    }
  }

  function parseInline(text: string): TextSegment[] {
    const segments: TextSegment[] = [];
    const pattern = /\*\*([^*]+)\*\*/g;
    let cursor = 0;

    for (const match of text.matchAll(pattern)) {
      const index = match.index ?? 0;
      if (index > cursor) {
        appendTokenSegments(segments, text.slice(cursor, index));
      }
      appendTokenSegments(segments, match[1], true);
      cursor = index + match[0].length;
    }

    if (cursor < text.length) {
      appendTokenSegments(segments, text.slice(cursor));
    }

    return segments.length > 0 ? segments : [{ text: "" }];
  }

  function isTableDivider(line: string) {
    return /^\s*\|?[\s:-]+\|[\s|:-]+\|?\s*$/.test(line);
  }

  function isTableRow(line: string) {
    const trimmed = line.trim();
    return trimmed.includes("|") && trimmed.split("|").length >= 3;
  }

  function tableCells(line: string) {
    return line
      .trim()
      .replace(/^\|/, "")
      .replace(/\|$/, "")
      .split("|")
      .map((cell, cellIndex) => {
        const trimmedCell = cell.trim();
        const segments = parseInline(trimmedCell);
        const uuid = segments.find((segment) => segment.uuid)?.uuid;
        const kind = uuid ? labelKind(trimmedCell) : undefined;
        return {
          segments: kind
            ? segments.map((segment) =>
                segment.uuid === uuid ? { ...segment, uuidKind: kind } : segment,
              )
            : segments,
          orderId:
            cellIndex === 0 || kind === "order"
              ? segments.find((segment) => segment.uuid)?.uuid
              : undefined,
          customerId:
            kind === "customer"
              ? segments.find((segment) => segment.uuid)?.uuid
              : undefined,
        };
      });
  }

  function inferListItemUuidKinds(segments: TextSegment[]) {
    let previousText = "";
    return segments.map((segment) => {
      if (!segment.uuid) {
        previousText += segment.text;
        return segment;
      }

      const context = previousText.slice(-32);
      previousText += segment.text;
      return { ...segment, uuidKind: labelKind(context) ?? segment.uuidKind };
    });
  }

  function handleOrderCellKeydown(e: KeyboardEvent, orderId?: string) {
    if (!orderId || (e.key !== "Enter" && e.key !== " ")) return;
    e.preventDefault();
    onOrderClick?.(orderId);
  }

  function handleCustomerClick(customerId: string) {
    onCustomerClick?.(customerId);
  }

  function parseMarkdown(markdown: string): MarkdownBlock[] {
    const lines = markdown.replace(/\r\n/g, "\n").split("\n");
    const parsed: MarkdownBlock[] = [];
    let index = 0;

    while (index < lines.length) {
      const line = lines[index];
      const trimmed = line.trim();

      if (!trimmed) {
        index += 1;
        continue;
      }

      if (trimmed.startsWith("```")) {
        const codeLines: string[] = [];
        index += 1;
        while (index < lines.length && !lines[index].trim().startsWith("```")) {
          codeLines.push(lines[index]);
          index += 1;
        }
        if (index < lines.length) index += 1;
        parsed.push({ type: "code", text: codeLines.join("\n") });
        continue;
      }

      if (
        isTableRow(line) &&
        index + 1 < lines.length &&
        isTableDivider(lines[index + 1])
      ) {
        const headers = tableCells(line).map((cell) => cell.segments);
        const rows: TableCell[][] = [];
        index += 2;
        while (
          index < lines.length &&
          isTableRow(lines[index]) &&
          lines[index].trim()
        ) {
          rows.push(tableCells(lines[index]));
          index += 1;
        }
        parsed.push({ type: "table", headers, rows });
        continue;
      }

      if (/^\s*[-*]\s+/.test(line)) {
        const items: TextSegment[][] = [];
        while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
          items.push(
            inferListItemUuidKinds(
              parseInline(lines[index].replace(/^\s*[-*]\s+/, "").trim()),
            ),
          );
          index += 1;
        }
        parsed.push({ type: "list", items });
        continue;
      }

      const paragraphLines: TextSegment[][] = [];
      while (
        index < lines.length &&
        lines[index].trim() &&
        !lines[index].trim().startsWith("```") &&
        !(
          isTableRow(lines[index]) &&
          index + 1 < lines.length &&
          isTableDivider(lines[index + 1])
        ) &&
        !/^\s*[-*]\s+/.test(lines[index])
      ) {
        paragraphLines.push(inferListItemUuidKinds(parseInline(lines[index].trim())));
        index += 1;
      }
      parsed.push({ type: "paragraph", lines: paragraphLines });
    }

    return parsed;
  }
</script>

{#snippet renderSegments(segments: TextSegment[])}
  {#each segments as segment}
    {#if segment.sku}
      <button
        class="tokenButton skuButton"
        type="button"
        title={`Add ${segment.sku} to order`}
        onclick={() => segment.sku && onSkuClick?.(segment.sku)}
      >
        {segment.text}
      </button>
    {:else if segment.uuid && segment.uuidKind === "customer"}
      <button
        class="tokenButton customerButton"
        type="button"
        title="View customer profile"
        aria-label={`View customer profile ${segment.uuid}`}
        onclick={() => segment.uuid && handleCustomerClick(segment.uuid)}
      >
        {segment.text}
      </button>
    {:else if segment.uuid}
      <button
        class="tokenButton orderButton"
        type="button"
        title="View order line items"
        aria-label={`View line items for order ${segment.uuid}`}
        onclick={() => segment.uuid && onOrderClick?.(segment.uuid)}
      >
        {segment.text}
      </button>
    {:else if segment.bold}
      <strong>{segment.text}</strong>
    {:else}
      {segment.text}
    {/if}
  {/each}
{/snippet}

{#each blocks as block}
  {#if block.type === "paragraph"}
    <p class="paragraph">
      {#each block.lines as line, lineIndex}
        {#if lineIndex > 0}<br />{/if}
        {@render renderSegments(line)}
      {/each}
    </p>
  {:else if block.type === "list"}
    <ul class="list">
      {#each block.items as item}
        <li>
          {@render renderSegments(item)}
        </li>
      {/each}
    </ul>
  {:else if block.type === "table"}
    <div class="tableWrap">
      <table>
        <thead>
          <tr>
            {#each block.headers as header}
              <th>
                {@render renderSegments(header)}
              </th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each block.rows as row}
            <tr>
              {#each row as cell}
                <td>
                  {#if cell.orderId}
                    <button
                      class="tableOrderButton"
                      type="button"
                      title="View order line items"
                      aria-label={`View line items for order ${cell.orderId}`}
                      onclick={() =>
                        cell.orderId && onOrderClick?.(cell.orderId)}
                      onkeydown={(e) => handleOrderCellKeydown(e, cell.orderId)}
                    >
                      {plainSegmentText(cell.segments)}
                    </button>
                  {:else}
                    {@render renderSegments(cell.segments)}
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <pre class="codeBlock"><code>{block.text}</code></pre>
  {/if}
{/each}

<style>
  .paragraph {
    margin: 0;
  }

  .paragraph + .paragraph,
  .paragraph + .list,
  .paragraph + .tableWrap,
  .list + .paragraph,
  .list + .tableWrap,
  .tableWrap + .paragraph {
    margin-top: 0.75rem;
  }

  .list {
    margin: 0;
    padding-left: 1.15rem;
  }

  .list li + li {
    margin-top: 0.25rem;
  }

  .tableWrap {
    max-width: 100%;
    overflow-x: auto;
    border: 1px solid rgba(15, 23, 42, 0.08);
    border-radius: 8px;
    background: #fff;
  }

  table {
    width: 100%;
    min-width: 36rem;
    border-collapse: collapse;
    font-size: 0.86rem;
    line-height: 1.35;
  }

  th,
  td {
    padding: 0.48rem 0.56rem;
    border-bottom: 1px solid rgba(15, 23, 42, 0.08);
    text-align: left;
    vertical-align: top;
    white-space: nowrap;
  }

  th {
    background: #f7faf8;
    color: #34433b;
    font-weight: 800;
  }

  tr:last-child td {
    border-bottom: 0;
  }

  .codeBlock {
    margin: 0;
    padding: 0.65rem;
    overflow-x: auto;
    border-radius: 8px;
    background: #0f172a;
    color: #e5e7eb;
    font-size: 0.84rem;
    line-height: 1.45;
  }

  .tokenButton {
    display: inline-flex;
    align-items: center;
    min-height: 1.45rem;
    margin: 0 0.1rem;
    padding: 0.08rem 0.32rem;
    border: 1px solid rgba(18, 140, 126, 0.22);
    border-radius: 6px;
    background: #eefaf3;
    color: #075e54;
    font: inherit;
    font-weight: 800;
    line-height: 1;
    cursor: pointer;
  }

  .tokenButton:hover {
    background: #dcf8c6;
    border-color: rgba(18, 140, 126, 0.38);
  }

  .tokenButton:focus-visible {
    outline: 2px solid rgba(18, 140, 126, 0.3);
    outline-offset: 2px;
  }

  .orderButton {
    max-width: 18rem;
    background: #eef8ff;
    color: #075985;
    border-color: rgba(14, 116, 144, 0.22);
    font-family: ui-monospace, SFMono-Regular, Consolas, "Liberation Mono",
      monospace;
    font-size: 0.78rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: middle;
  }

  .orderButton:hover {
    background: #dff3ff;
    border-color: rgba(14, 116, 144, 0.38);
  }

  .tableOrderButton {
    width: 100%;
    padding: 0;
    border: 0;
    background: transparent;
    color: inherit;
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  .tableOrderButton:hover {
    color: #075985;
    text-decoration: underline;
  }

  .tableOrderButton:focus-visible {
    outline: 2px solid rgba(14, 116, 144, 0.32);
    outline-offset: 2px;
    border-radius: 4px;
  }
</style>
