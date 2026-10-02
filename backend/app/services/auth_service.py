from fastapi import HTTPException, status

from app.appwrite.repositories import Repositories
from app.core.security import (
    create_tokens,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.atendente import PerfilAtendente


class AuthService:
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def login(self, email: str, senha: str) -> dict:
        user = await self.repos.atendentes.get_by_email(email)
        if not user or not verify_password(senha, user["hash_senha"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválidos",
            )
        if not user["ativo"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo",
            )
        return create_tokens(user["id"], user["perfil"])

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if payload is None or payload.get("typ") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        user_id = payload.get("sub")
        user = await self.repos.atendentes.get(user_id)
        if not user or not user["ativo"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
            )
        return create_tokens(user["id"], user["perfil"])

    async def alterar_senha(self, user: dict, senha_atual: str, nova_senha: str) -> None:
        if not verify_password(senha_atual, user["hash_senha"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta",
            )
        await self.repos.atendentes.update(
            user["id"], {"hash_senha": hash_password(nova_senha)}
        )

    async def criar_usuario(self, data: dict, user_logado: dict) -> dict:
        perfil_solicitado = data.get("perfil", "atendente")
        if user_logado["perfil"] == PerfilAtendente.supervisor:
            if perfil_solicitado != "atendente":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor só pode criar usuários com perfil 'atendente'",
                )
        if await self.repos.atendentes.get_by_email(data["email"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )
        return await self.repos.atendentes.create(
            {
                "nome": data["nome"],
                "email": data["email"],
                "hash_senha": hash_password(data["senha"]),
                "perfil": perfil_solicitado,
            }
        )

    async def listar_usuarios(self) -> list[dict]:
        users = await self.repos.atendentes.list_all()
        users.sort(key=lambda u: u.get("nome") or "")
        return users

    async def obter_usuario(self, usuario_id: str) -> dict:
        usuario = await self.repos.atendentes.get(usuario_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return usuario

    async def atualizar_usuario(
        self, usuario_id: str, data: dict, user_logado: dict
    ) -> dict:
        usuario = await self.obter_usuario(usuario_id)

        update: dict = {}
        if "perfil" in data and data["perfil"] is not None:
            if user_logado["perfil"] != PerfilAtendente.admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Apenas admin pode alterar perfil de usuário",
                )
            update["perfil"] = data["perfil"]
        if "nome" in data and data["nome"] is not None:
            update["nome"] = data["nome"]
        if "email" in data and data["email"] is not None:
            update["email"] = data["email"]
        if "ativo" in data and data["ativo"] is not None:
            update["ativo"] = data["ativo"]
        if not update:
            return usuario
        return await self.repos.atendentes.update(usuario_id, update)

    async def remover_usuario(self, usuario_id: str) -> None:
        await self.obter_usuario(usuario_id)
        await self.repos.atendentes.update(usuario_id, {"ativo": False})
