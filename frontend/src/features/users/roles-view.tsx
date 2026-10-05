"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { AppSelect } from "@/components/common/app-select"
import { EmptyState } from "@/components/common/empty-state"
import { PageHeader } from "@/components/common/page-header"
import { Card } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { useAuth } from "@/features/auth/auth-provider"
import { usersApi } from "@/lib/api/endpoints"
import type { UserRole } from "@/lib/api/types"
import { formatDateTime, ROLE_LABEL } from "@/lib/format"
import { queryKeys } from "@/lib/query-keys"

const roleOptions = (Object.keys(ROLE_LABEL) as UserRole[]).map((r) => ({ value: r, label: ROLE_LABEL[r] }))

export function RolesView() {
  const { isAdmin, me } = useAuth()
  const queryClient = useQueryClient()
  const users = useQuery({ queryKey: queryKeys.users, queryFn: usersApi.list, enabled: isAdmin })
  const update = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => usersApi.updateRole(id, role),
    onSuccess: (profile) => {
      toast.success(`${profile.email}: ${ROLE_LABEL[profile.role]}`)
      void queryClient.invalidateQueries({ queryKey: queryKeys.users })
    },
  })

  if (!isAdmin) return <EmptyState title="Bu sahifa faqat admin uchun" />

  return (
    <>
      <PageHeader title="Rollar" subtitle="Foydalanuvchilar va ularning huquqlari" />
      <Card className="px-2 py-2">
        <Table>
          <TableHeader>
            <TableRow className="text-xs uppercase">
              <TableHead>Foydalanuvchi</TableHead>
              <TableHead>Email</TableHead>
              <TableHead>Qo&apos;shilgan</TableHead>
              <TableHead className="w-48">Rol</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.isPending && (
              <TableRow>
                <TableCell colSpan={4}>
                  <Skeleton className="h-5" />
                </TableCell>
              </TableRow>
            )}
            {users.data?.map((user) => (
              <TableRow key={user.id}>
                <TableCell className="font-medium">{user.full_name ?? "—"}</TableCell>
                <TableCell>{user.email}</TableCell>
                <TableCell className="text-sm text-muted-foreground">{formatDateTime(user.created_at)}</TableCell>
                <TableCell>
                  <AppSelect
                    value={user.role}
                    options={roleOptions}
                    disabled={user.id === me?.user_id || update.isPending}
                    onChange={(role) => update.mutate({ id: user.id, role })}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      <p className="mt-3 text-xs text-muted-foreground">
        Admin — hamma narsa; Menejer — kirim/chiqim/to&apos;lov va AI buyruqlar; Kuzatuvchi — faqat ko&apos;rish.
      </p>
    </>
  )
}
