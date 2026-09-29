"use client";

import { Box, Paper, Typography, useTheme } from "@mui/material";
import * as d3 from "d3";
import { useEffect, useMemo, useRef, useState } from "react";

type RevenuePoint = { month: string; revenue: number };

/** Interactive D3 monthly revenue bar chart. */
export function RevenueChart({ data }: { data: RevenuePoint[] }) {
  const ref = useRef<SVGSVGElement | null>(null);
  const theme = useTheme();
  const [tooltip, setTooltip] = useState<{ x: number; y: number; label: string } | null>(null);
  const chartData = useMemo(() => data.filter((point) => Number.isFinite(point.revenue)), [data]);

  useEffect(() => {
    const svg = d3.select(ref.current);
    svg.selectAll("*").remove();
    const width = 760;
    const height = 320;
    const margin = { top: 24, right: 24, bottom: 48, left: 72 };
    svg.attr("viewBox", `0 0 ${width} ${height}`).attr("role", "img").attr("aria-label", "Monthly revenue bar chart");
    svg.append("title").text("Monthly revenue by order month");

    if (!chartData.length) {
      svg
        .append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", theme.palette.text.secondary)
        .text("No revenue data available");
      return;
    }

    const x = d3
      .scaleBand()
      .domain(chartData.map((point) => point.month))
      .range([margin.left, width - margin.right])
      .padding(0.18);
    const y = d3
      .scaleLinear()
      .domain([0, d3.max(chartData, (point) => point.revenue) ?? 0])
      .nice()
      .range([height - margin.bottom, margin.top]);

    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).tickSizeOuter(0))
      .selectAll("text")
      .attr("transform", "rotate(-30)")
      .attr("text-anchor", "end")
      .attr("fill", theme.palette.text.secondary);

    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(
        d3
          .axisLeft(y)
          .ticks(5)
          .tickFormat((value) => d3.format("$.2s")(Number(value))),
      )
      .call((group) => group.select(".domain").remove())
      .call((group) => group.selectAll("text").attr("fill", theme.palette.text.secondary));

    svg
      .append("g")
      .attr("stroke", theme.palette.divider)
      .attr("stroke-opacity", 0.7)
      .call((group) =>
        group
          .selectAll("line")
          .data(y.ticks(5))
          .join("line")
          .attr("x1", margin.left)
          .attr("x2", width - margin.right)
          .attr("y1", (value) => y(value))
          .attr("y2", (value) => y(value)),
      );

    svg
      .append("g")
      .selectAll("rect")
      .data(chartData)
      .join("rect")
      .attr("x", (point) => x(point.month) ?? 0)
      .attr("y", (point) => y(point.revenue))
      .attr("width", x.bandwidth())
      .attr("height", (point) => y(0) - y(point.revenue))
      .attr("rx", 6)
      .attr("fill", theme.palette.primary.main)
      .attr("tabindex", 0)
      .attr("aria-label", (point) => `${point.month}: ${d3.format("$,.2f")(point.revenue)}`)
      .on("mouseenter focus", (event: MouseEvent | FocusEvent, point) => {
        const x = event instanceof MouseEvent ? event.offsetX : width / 2;
        const y = event instanceof MouseEvent ? event.offsetY : margin.top;
        setTooltip({ x, y, label: `${point.month}: ${d3.format("$,.2f")(point.revenue)}` });
      })
      .on("mouseleave blur", () => setTooltip(null));
  }, [chartData, theme]);

  return (
    <Paper variant="outlined" sx={{ p: 2, position: "relative" }}>
      <Typography variant="h6" gutterBottom>
        Monthly revenue
      </Typography>
      <Box component="svg" ref={ref} sx={{ width: "100%", height: "auto", display: "block" }} />
      {tooltip && (
        <Paper
          elevation={6}
          sx={{
            position: "absolute",
            left: tooltip.x + 12,
            top: tooltip.y + 12,
            px: 1,
            py: 0.5,
            pointerEvents: "none",
          }}
        >
          <Typography variant="caption">{tooltip.label}</Typography>
        </Paper>
      )}
    </Paper>
  );
}
