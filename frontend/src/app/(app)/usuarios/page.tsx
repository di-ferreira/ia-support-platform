"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/stores/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select as SelectNative } from "@/components/ui/select";
import { UserPlus, Pencil, ShieldCheck, Shield, User } from "lucide-react";
import { useState } from "react";

export default function UsuariosPage() {
  const queryClient = useQueryClient();
  const { user: currentUser } = useAuthStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [editUser, setEditUser] = useState<any>(null);
  const isAdmin = currentUser?.perfil === "admin";

  const profileIcon = (perfil: string) => {
    switch (perfil) {
      case "admin": return <ShieldCheck className="h-4 w-4 text-red-500" />;
      case "supervisor": return <Shield className="h-4 w-4 text-orange-500" />;
      default: return <User className="h-4 w-4 text-blue-500" />;
    }
  };

  const profileColors: Record<string, string> = {
    admin: "danger",
    supervisor: "warning",
    atendente: "info",
  };

  const { data: usuarios } = useQuery({
    queryKey: ["usuarios"],
    queryFn: () => api.get<any[]>("/auth/usuarios"),
  });

  const toggleAtivo = useMutation({
    mutationFn: ({ id, ativo }: { id: number; ativo: boolean }) =>
      api.patch(`/auth/usuarios/${id}`, { ativo }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["usuarios"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-gray-900">Usuários</h1>
        <Button onClick={() => { setEditUser(null); setModalOpen(true); }}>
          <UserPlus className="h-4 w-4 mr-2" /> Novo Usuário
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Todos os Usuários</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="pb-3 font-medium">Nome</th>
                  <th className="pb-3 font-medium">Email</th>
                  <th className="pb-3 font-medium">Perfil</th>
                  <th className="pb-3 font-medium">Status</th>
                  {isAdmin && <th className="pb-3 font-medium">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {usuarios?.map((u: any) => (
                  <tr key={u.id} className="border-b last:border-0">
                    <td className="py-3 text-gray-900">{u.nome}</td>
                    <td className="py-3 text-gray-500">{u.email}</td>
                    <td className="py-3">
                      <Badge variant={(profileColors[u.perfil] || "neutral") as any} className="flex items-center gap-1 w-fit">
                        {profileIcon(u.perfil)}
                        <span className="capitalize">{u.perfil}</span>
                      </Badge>
                    </td>
                    <td className="py-3">
                      {isAdmin ? (
                        <button
                          onClick={() => toggleAtivo.mutate({ id: u.id, ativo: !u.ativo })}
                          className={`text-xs font-medium px-2 py-1 rounded-full ${
                            u.ativo
                              ? "bg-green-100 text-green-700 hover:bg-green-200"
                              : "bg-red-100 text-red-700 hover:bg-red-200"
                          }`}
                        >
                          {u.ativo ? "Ativo" : "Inativo"}
                        </button>
                      ) : (
                        <span className={`text-xs font-medium px-2 py-1 rounded-full ${
                          u.ativo ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                        }`}>
                          {u.ativo ? "Ativo" : "Inativo"}
                        </span>
                      )}
                    </td>
                    {isAdmin && (
                      <td className="py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => { setEditUser(u); setModalOpen(true); }}
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {modalOpen && (
        <UserFormModal
          user={editUser}
          isAdmin={isAdmin}
          onClose={() => setModalOpen(false)}
          onSaved={() => {
            setModalOpen(false);
            queryClient.invalidateQueries({ queryKey: ["usuarios"] });
          }}
        />
      )}
    </div>
  );
}

function UserFormModal({
  user,
  isAdmin,
  onClose,
  onSaved,
}: {
  user: any;
  isAdmin: boolean;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nome, setNome] = useState(user?.nome || "");
  const [email, setEmail] = useState(user?.email || "");
  const [senha, setSenha] = useState("");
  const [perfil, setPerfil] = useState(user?.perfil || "atendente");
  const [error, setError] = useState("");

  const createMutation = useMutation({
    mutationFn: (data: any) => api.post("/auth/usuarios", data),
    onSuccess: onSaved,
    onError: (err: any) => setError(err?.detail || "Erro ao criar usuário"),
  });

  const updateMutation = useMutation({
    mutationFn: (data: any) => api.patch(`/auth/usuarios/${user.id}`, data),
    onSuccess: onSaved,
    onError: (err: any) => setError(err?.detail || "Erro ao atualizar usuário"),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    if (user) {
      const payload: any = {};
      if (nome !== user.nome) payload.nome = nome;
      if (email !== user.email) payload.email = email;
      if (perfil !== user.perfil) payload.perfil = perfil;
      if (senha) payload.senha = senha;
      if (Object.keys(payload).length === 0) return;
      updateMutation.mutate(payload);
    } else {
      if (!senha) { setError("Senha é obrigatória"); return; }
      createMutation.mutate({ nome, email, senha, perfil });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {user ? "Editar Usuário" : "Novo Usuário"}
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome</label>
            <Input value={nome} onChange={(e) => setNome(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {user ? "Nova senha (deixe em branco para manter)" : "Senha"}
            </label>
            <Input type="password" value={senha} onChange={(e) => setSenha(e.target.value)} required={!user} />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Perfil</label>
            <SelectNative value={perfil} onChange={(e) => setPerfil(e.target.value)}>
              {isAdmin ? (
                <>
                  <option value="admin">Admin</option>
                  <option value="supervisor">Supervisor</option>
                </>
              ) : null}
              <option value="atendente">Atendente</option>
            </SelectNative>
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={onClose}>Cancelar</Button>
            <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
              {user ? "Salvar" : "Criar"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
