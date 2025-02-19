import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import os
import calendar
from datetime import datetime
from io import BytesIO

def processar_nfe(xml_file):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except ET.ParseError:
        return None

    nfe_info = root.find(".//nfe:NFe/nfe:infNFe", ns)
    if nfe_info is None:
        return None

    num_nota_fiscal = nfe_info.find("nfe:ide/nfe:nNF", ns)
    num_nota_fiscal = num_nota_fiscal.text if num_nota_fiscal is not None else "Desconhecido"

    serie_nota_fiscal = nfe_info.find("nfe:ide/nfe:serie", ns)
    serie_nota_fiscal = serie_nota_fiscal.text if serie_nota_fiscal is not None else "Desconhecido"

    fornecedor = nfe_info.find("nfe:emit/nfe:xNome", ns)
    fornecedor = fornecedor.text if fornecedor is not None else "Desconhecido"

    total_info = nfe_info.find("nfe:total/nfe:ICMSTot/nfe:vProd", ns)
    valor_total_produtos = float(total_info.text) if total_info is not None else 0.00

    natureza_operacao = nfe_info.find("nfe:ide/nfe:natOp", ns)
    natureza_operacao = natureza_operacao.text if natureza_operacao is not None else "Desconhecido"

    nota_fiscal_com_serie = f"{num_nota_fiscal} - {serie_nota_fiscal}"

    data = []
    for det in nfe_info.findall("nfe:det", ns):
        produto = det.find("nfe:prod/nfe:xProd", ns).text or "Produto Desconhecido"
        quantidade_total = float(det.find("nfe:prod/nfe:qCom", ns).text or 0)
        unidade = det.find("nfe:prod/nfe:uCom", ns).text or "UN"

        rastros = det.findall("nfe:prod/nfe:rastro", ns)
        if rastros:
            quantidade_por_lote = quantidade_total / len(rastros)
            for rastro in rastros:
                lote = rastro.find("nfe:nLote", ns)
                lote = lote.text if lote is not None else "Sem Lote"

                validade = rastro.find("nfe:dVal", ns)
                validade = validade.text if validade is not None else "Sem Validade"

                partes = validade.split("-")
                if len(partes) == 3:
                    validade = f"{partes[2]}/{partes[1]}/{partes[0]}"
                elif len(partes) == 2:
                    try:
                        ultimo_dia = calendar.monthrange(int(partes[0]), int(partes[1]))[1]
                        validade = f"{ultimo_dia}/{partes[1]}/{partes[0]}"
                    except ValueError:
                        validade = "Data Inválida"

                data.append([datetime.now().strftime("%d/%m/%Y"), nota_fiscal_com_serie, fornecedor, produto, quantidade_por_lote, unidade, lote, validade, valor_total_produtos, natureza_operacao])
        else:
            data.append([datetime.now().strftime("%d/%m/%Y"), nota_fiscal_com_serie, fornecedor, produto, quantidade_total, unidade, "Sem Lote", None, valor_total_produtos, natureza_operacao])

    return data

def processar_arquivos_xml(arquivos):
    todas_as_notas = []
    for arquivo in arquivos:
        dados_nota = processar_nfe(arquivo)
        if dados_nota:
            todas_as_notas.extend(dados_nota)

    df = pd.DataFrame(todas_as_notas, columns=[
        "DATA", "NOTA FISCAL", "FORNECEDOR", "PRODUTO", "QUANTIDADE", "UNIDADE", "LOTE", "VALIDADE", "VALOR TOTAL PRODUTOS", "NATUREZA DA OPERAÇÃO"
    ])

    df["VALOR TOTAL PRODUTOS"] = df["VALOR TOTAL PRODUTOS"].apply(lambda x: f"R${x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    return df

def main():
    st.title("Processador de Notas Fiscais Eletrônicas (NFe)")
    uploaded_files = st.file_uploader("Envie os arquivos XML das notas fiscais", accept_multiple_files=True, type=["xml"])

    if uploaded_files:
        if st.button("Processar Notas"):
            df_resultado = processar_arquivos_xml(uploaded_files)

            if not df_resultado.empty:
                st.success("Processamento concluído! Baixe o arquivo abaixo.")

                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_resultado.to_excel(writer, index=False)
                output.seek(0)

                st.download_button(
                    label="Baixar Excel com as notas fiscais",
                    data=output,
                    file_name="notas_fiscais.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.error("Nenhuma nota fiscal válida foi processada.")

if __name__ == "__main__":
    main()
