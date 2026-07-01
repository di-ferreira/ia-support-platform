from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_tokens,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.atendente import Atendente, PerfilAtendente


class AuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def login(self, email: str, senha: str) -> dict:
        result = await self.session.execute(
            select(Atendente).where(Atendente.email == email)
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(senha, user.hash_senha):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha inválidos",
            )
        if not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário inativo",
            )
        return create_tokens(user.id, user.perfil.value)

    async def refresh(self, refresh_token: str) -> dict:
        payload = decode_token(refresh_token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido"
            )
        user_id = payload.get("sub")
        result = await self.session.execute(
            select(Atendente).where(Atendente.id == int(user_id))
        )
        user = result.scalar_one_or_none()
        if not user or not user.ativo:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado"
            )
        return create_tokens(user.id, user.perfil.value)

    async def alterar_senha(
        self, user: Atendente, senha_atual: str, nova_senha: str
    ) -> None:
        if not verify_password(senha_atual, user.hash_senha):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta",
            )
        user.hash_senha = hash_password(nova_senha)
        await self.session.commit()

    async def criar_usuario(
        self, data: dict, user_logado: Atendente
    ) -> Atendente:
        perfil_solicitado = data.get("perfil", "atendente")
        if user_logado.perfil == PerfilAtendente.supervisor:
            if perfil_solicitado != "atendente":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Supervisor só pode criar usuários com perfil 'atendente'",
                )
        result = await self.session.execute(
            select(Atendente).where(Atendente.email == data["email"])
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )
        usuario = Atendente(
            nome=data["nome"],
            email=data["email"],
            hash_senha=hash_password(data["senha"]),
            perfil=PerfilAtendente(perfil_solicitado),
        )
        self.session.add(usuario)
        await self.session.commit()
        await self.session.refresh(usuario)
        return usuario

    async def listar_usuarios(self) -> list[Atendente]:
        result = await self.session.execute(
            select(Atendente).order_by(Atendente.nome)
        )
        return list(result.scalars().all())

    async def obter_usuario(self, usuario_id: int) -> Atendente:
        result = await self.session.execute(
            select(Atendente).where(Atendente.id == usuario_id)
        )
        usuario = result.scalar_one_or_none()
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return usuario

    async def atualizar_usuario(
        self, usuario_id: int, data: dict, user_logado: Atendente
    ) -> Atendente:
        usuario = await self.obter_usuario(usuario_id)

        if "perfil" in data and data["perfil"] is not None:
            if user_logado.perfil != PerfilAtendente.admin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Apenas admin pode alterar perfil de usuário",
                )
            usuario.perfil = PerfilAtendente(data["perfil"])

        if "nome" in data and data["nome"] is not None:
            usuario.nome = data["nome"]
        if "email" in data and data["email"] is not None:
            usuario.email = data["email"]
        if "ativo" in data and data["ativo"] is not None:
            usuario.ativo = data["ativo"]

        await self.session.commit()
        await self.session.refresh(usuario)
        return usuario

    async def remover_usuario(self, usuario_id: int) -> None:
        usuario = await self.obter_usuario(usuario_id)
        usuario.ativo = False
        await self.session.commit()
