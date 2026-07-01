"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Smartphone,
  QrCode,
  Plug,
  PlugZap,
  Trash2,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { useState } from "react";

const INSTANCE_NAME = "emsoft-support";

export default function ConfiguracoesPage() {
  const queryClient = useQueryClient();
  const [instanceName, setInstanceName] = useState(INSTANCE_NAME);
  const [qrCodeImg, setQrCodeImg] = useState<string | null>(null);

  const { data: statusData, isLoading: statusLoading } = useQuery({
    queryKey: ["evolution-status", instanceName],
    queryFn: () => api.get<any>(`/evolution/instance/status/${instanceName}`),
    retry: false,
    refetchInterval: 15000,
  });

  const connected =
    statusData?.state === "open" || statusData?.connected === true;

  const createInstance = useMutation({
    mutationFn: () =>
      api.post("/evolution/instance", { instanceName }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["evolution-status"] });
    },
  });

  const showQrCode = useMutation({
    mutationFn: () =>
      api.get<any>(`/evolution/instance/qrcode/${instanceName}`),
    onSuccess: (data) => {
      setQrCodeImg(data.base64 || data.qrcode || null);
    },
  });

  const disconnect = useMutation({
    mutationFn: () =>
      api.post(`/evolution/instance/disconnect/${instanceName}`),
    onSuccess: () => {
      setQrCodeImg(null);
      queryClient.invalidateQueries({ queryKey: ["evolution-status"] });
    },
  });

  const setupWebhook = useMutation({
    mutationFn: () =>
      api.post(`/evolution/instance/webhook/default/${instanceName}`),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Configurações</h1>
        <p className="text-gray-500 mt-1">Integração WhatsApp via Evolution API</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Status Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Smartphone className="h-5 w-5" />
              Status da Instância
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <Input
                  value={instanceName}
                  onChange={(e) => setInstanceName(e.target.value)}
                  placeholder="Nome da instância"
                  className="w-48"
                />
              </div>
              {statusLoading ? (
                <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
              ) : connected ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <XCircle className="h-5 w-5 text-red-500" />
              )}
            </div>
            {statusData && (
              <div className="text-sm text-gray-600 space-y-1">
                <p>
                  <span className="font-medium">Estado:</span>{" "}
                  {statusData.state || statusData.status || "desconhecido"}
                </p>
              </div>
            )}
            {statusData?.error && (
              <p className="text-sm text-red-500">{statusData.error}</p>
            )}

            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                onClick={() => createInstance.mutate()}
                disabled={createInstance.isPending}
              >
                {createInstance.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <Plug className="h-4 w-4 mr-1" />
                )}
                Criar Instância
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => showQrCode.mutate()}
                disabled={showQrCode.isPending}
              >
                {showQrCode.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <QrCode className="h-4 w-4 mr-1" />
                )}
                Exibir QR Code
              </Button>
              <Button
                size="sm"
                variant="secondary"
                onClick={() => setupWebhook.mutate()}
                disabled={setupWebhook.isPending}
              >
                {setupWebhook.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-1" />
                ) : (
                  <PlugZap className="h-4 w-4 mr-1" />
                )}
                Configurar Webhook
              </Button>
              {connected && (
                <Button
                  size="sm"
                  variant="danger"
                  onClick={() => disconnect.mutate()}
                  disabled={disconnect.isPending}
                >
                  {disconnect.isPending ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <Trash2 className="h-4 w-4 mr-1" />
                  )}
                  Desconectar
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* QR Code Card */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <QrCode className="h-5 w-5" />
              Escanear QR Code
            </CardTitle>
          </CardHeader>
          <CardContent>
            {qrCodeImg ? (
              <div className="flex flex-col items-center gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={qrCodeImg}
                  alt="WhatsApp QR Code"
                  className="w-64 h-64 border rounded-lg"
                />
                <p className="text-sm text-gray-500">
                  Abra o WhatsApp no celular e escaneie o QR code
                </p>
              </div>
            ) : (
              <div className="flex flex-col items-center py-8 text-gray-400">
                <QrCode className="h-16 w-16 mb-3" />
                <p className="text-sm">
                  {connected
                    ? "WhatsApp já conectado"
                    : "Clique em 'Exibir QR Code' para conectar"}
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Actions feedback */}
      {createInstance.isSuccess && (
        <Card>
          <CardContent className="text-sm text-green-600 flex items-center gap-2 py-3">
            <CheckCircle2 className="h-4 w-4" />
            Instância criada com sucesso! Escaneie o QR code para conectar.
          </CardContent>
        </Card>
      )}
      {setupWebhook.isSuccess && (
        <Card>
          <CardContent className="text-sm text-green-600 flex items-center gap-2 py-3">
            <CheckCircle2 className="h-4 w-4" />
            Webhook configurado para n8n!
          </CardContent>
        </Card>
      )}
      {disconnect.isSuccess && (
        <Card>
          <CardContent className="text-sm text-green-600 flex items-center gap-2 py-3">
            <CheckCircle2 className="h-4 w-4" />
            Desconectado com sucesso.
          </CardContent>
        </Card>
      )}
      {(createInstance.isError ||
        showQrCode.isError ||
        disconnect.isError ||
        setupWebhook.isError) && (
        <Card>
          <CardContent className="text-sm text-red-600 flex items-center gap-2 py-3">
            <XCircle className="h-4 w-4" />
            Erro: {(createInstance.error?.message ||
              showQrCode.error?.message ||
              disconnect.error?.message ||
              setupWebhook.error?.message)}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
