import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { InvoiceTable } from "@/features/invoices/invoice-table"
import type { Invoice } from "@/lib/api/types"

function invoice(overrides: Partial<Invoice>): Invoice {
  return {
    id: crypto.randomUUID(),
    number: "INV-00000000-202609",
    type: "chiqim",
    status: "accepted",
    payment_status: "unpaid",
    counterparty: { id: "c1", kind: "client", name: "Elbek Baxt uyi" },
    subtotal: 1000,
    discount_percent: 0,
    discount_amount: 0,
    total: 1000,
    paid_amount: 0,
    note: null,
    source: "web",
    created_at: "2026-09-12T10:00:00Z",
    ...overrides,
  }
}

describe("InvoiceTable", () => {
  it("batafsil rejimda jo'natuvchi/qabul qiluvchini tur bo'yicha to'g'ri ko'rsatadi", () => {
    render(
      <InvoiceTable
        detailed
        loading={false}
        onOpen={vi.fn()}
        invoices={[
          invoice({ number: "INV-kirim", type: "kirim", counterparty: { id: "s", kind: "supplier", name: "Sof food" } }),
          invoice({ number: "INV-chiqim" }),
          invoice({ number: "INV-util", type: "utilizatsiya", counterparty: null }),
        ]}
      />,
    )
    const cells = (number: string) =>
      within(screen.getByText(number).closest("tr")!).getAllByRole("cell").map((c) => c.textContent)

    expect(cells("INV-kirim")).toEqual(expect.arrayContaining(["Sof food", "Ombor"]))
    expect(cells("INV-chiqim").slice(-3, -1)).toEqual(["Ombor", "Elbek Baxt uyi"])
    expect(cells("INV-util")).toContain("Hisobdan chiqarildi")
    // Utilizatsiyada to'lov holati ma'nosiz — chiziqcha
    expect(cells("INV-util")).toContain("—")
  })

  it("AI yaratgan hujjatni belgilaydi", () => {
    render(<InvoiceTable loading={false} onOpen={vi.fn()} invoices={[invoice({ source: "ai" })]} />)
    expect(screen.getByLabelText("AI orqali")).toBeInTheDocument()
  })

  it("tanlash rejimida faqat to'lanmagan invoicelar uchun checkbox chiqadi", async () => {
    const onToggle = vi.fn()
    const unpaid = invoice({ number: "INV-a" })
    render(
      <InvoiceTable
        selectable
        selected={new Set()}
        onToggle={onToggle}
        loading={false}
        onOpen={vi.fn()}
        invoices={[unpaid, invoice({ number: "INV-b", payment_status: "paid" })]}
      />,
    )
    expect(screen.getAllByRole("checkbox")).toHaveLength(1)
    await userEvent.click(screen.getByRole("checkbox", { name: "INV-a ni tanlash" }))
    expect(onToggle).toHaveBeenCalledWith(unpaid.id)
  })

  it("Batafsil tugmasi invoice id bilan chaqiradi", async () => {
    const onOpen = vi.fn()
    const item = invoice({})
    render(<InvoiceTable loading={false} onOpen={onOpen} invoices={[item]} />)
    await userEvent.click(screen.getByRole("button", { name: "Batafsil" }))
    expect(onOpen).toHaveBeenCalledWith(item.id)
  })

  it("bo'sh ro'yxatda xabar ko'rsatadi", () => {
    render(<InvoiceTable loading={false} onOpen={vi.fn()} invoices={[]} />)
    expect(screen.getByText("Invoicelar topilmadi")).toBeInTheDocument()
  })
})
