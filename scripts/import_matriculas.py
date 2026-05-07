"""Placeholder para importador de CSV de matrículas.

Item 4 do plano técnico.

Schema esperado do CSV (a confirmar com o usuário quando ele exportar
da base atual do cartório):

    numero,livro_folha,proprietario_atual_nome,cpf_cnpj,
    endereco_logradouro,endereco_numero,endereco_bairro,
    area_descrita_texto,area_descrita_m2,observacoes

CPF/CNPJ é hashado (SHA-256 + salt da settings) ao salvar; campo `cpf_cnpj`
é opcional.
"""

if __name__ == "__main__":
    raise SystemExit("Não implementado ainda — ver item 4 do plano técnico.")
