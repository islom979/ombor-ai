import { useQueryClient } from "@tanstack/react-query"
import { useCallback } from "react"

import { queryKeys } from "@/lib/query-keys"

/** Ombor holatini o'zgartiruvchi har qanday amaldan keyin bog'liq keshlarni yangilaydi. */
export function useInvalidateWarehouse() {
  const queryClient = useQueryClient()
  return useCallback(() => {
    for (const key of [
      queryKeys.stock.all,
      queryKeys.products.all,
      queryKeys.invoices.all,
      queryKeys.counterparties.all,
      queryKeys.payments.all,
      queryKeys.payments.registers,
      ["statistics"],
    ]) {
      void queryClient.invalidateQueries({ queryKey: key })
    }
  }, [queryClient])
}
