import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { PaginationBar } from "@/components/common/pagination-bar"
import { StatCard } from "@/components/common/stat-card"
import { InvoiceTypeBadge, PaymentStatusBadge } from "@/components/common/status-badges"

describe("PaginationBar", () => {
  it("sahifa ma'lumotini ko'rsatadi va chegaralarda tugmalarni o'chiradi", async () => {
    const onChange = vi.fn()
    const { rerender } = render(<PaginationBar page={1} pages={3} total={42} onChange={onChange} />)
    expect(screen.getByText("Sahifa 1 / 3 · Jami: 42 ta")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Oldingi" })).toBeDisabled()

    await userEvent.click(screen.getByRole("button", { name: "Keyingi" }))
    expect(onChange).toHaveBeenCalledWith(2)

    rerender(<PaginationBar page={3} pages={3} total={42} onChange={onChange} />)
    expect(screen.getByRole("button", { name: "Keyingi" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Oldingi" })).toBeEnabled()
  })
})

describe("StatCard", () => {
  it("yuklanayotganda qiymat o'rniga skeleton ko'rsatadi", () => {
    const { rerender } = render(<StatCard label="Kam qolgan" value={7} loading />)
    expect(screen.queryByText("7")).not.toBeInTheDocument()
    rerender(<StatCard label="Kam qolgan" value={7} tone="danger" />)
    expect(screen.getByText("7")).toHaveClass("text-destructive")
  })
})

describe("status badges", () => {
  it("o'zbekcha yorliqlar", () => {
    render(
      <>
        <PaymentStatusBadge status="unpaid" />
        <PaymentStatusBadge status="partial" />
        <PaymentStatusBadge status="paid" />
        <InvoiceTypeBadge type="utilizatsiya" />
      </>,
    )
    for (const label of ["To'lanmagan", "Qisman to'langan", "To'langan", "Utilizatsiya"]) {
      expect(screen.getByText(label)).toBeInTheDocument()
    }
  })
})
