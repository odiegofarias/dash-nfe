import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import os
import re
from io import BytesIO

def extrair_lotes_validade(info_adicional):
    lotes_validade = []
    
    lotes_1 = re.findall(r'LOTE:\s*([A-Za-z0-9]+)', info_adicional, re.IGNORECASE)
    validades_1 = re.findall(r'VAL:\s*(\d{2}/\d{2}/\d{4}|\d{2}/\d{2})', info_adicional, re.IGNORECASE)
    
    serie_match = re.search(r'No\(s\) de Serie:\s*(.*)', info_adicional, re.IGNORECASE)
    validades_2 = re.findall(r'Venc\.\s*(\d{2}/\d{2}/\d{4})', info_adicional, re.IGNORECASE)
    
    lotes_2 = []
    if serie_match:
        lotes_2 = re.split(r',\s*', serie_match.group(1))
        lotes_2 = [re.sub(r'Venc\.\s*\d{2}/\d{2}/\d{4}', '', l).strip() for l in lotes_2]
    
    lotes = lotes_1 + lotes_2
    validades = validades_1 + validades_2
    
    min_length = min(len(lotes), len(validades))
    for i in range(min_length):
        lotes_validade.append((lotes[i], validades[i]))
    
    for i in range(min_length, len(lotes)):
        lotes_validade.append((lotes[i], None))
    
    return lotes_validade

def extrair_lotes_rastro(det, ns):
    lotes_validade = []
    for rastro in det.findall("nfe:prod/nfe:rastro", ns):
        lote = rastro.find("nfe:nLote", ns).text
        validade = rastro.find("nfe:dVal", ns).text
        lotes_validade.append((lote, validade))
    return lotes_validade

def processar_nfe(xml_file):
    ns = {"nfe": "http://www.portalfiscal.inf.br/nfe"}
    tree = ET.parse(xml_file)
    root = tree.getroot()
    
    nfe_info = root.find(".//nfe:NFe/nfe:infNFe", ns)
    if nfe_info is None:
        return None  
    
    num_nota_fiscal = nfe_info.find("nfe:ide/nfe:nNF", ns).text
    serie_nota_fiscal = nfe_info.find("nfe:ide/nfe:serie", ns).text
    natureza_operacao = nfe_info.find("nfe:ide/nfe:natOp", ns).text
    chave_nota_fiscal = nfe_info.attrib["Id"].replace("NFe", "")
    fornecedor = nfe_info.find("nfe:emit/nfe:xNome", ns).text
    
    data = []
    
    for det in nfe_info.findall("nfe:det", ns):
        produto = det.find("nfe:prod/nfe:xProd", ns).text
        quantidade_total = int(float(det.find("nfe:prod/nfe:qCom", ns).text))
        
        info_adicional = det.find("nfe:infAdProd", ns)
        lotes_validade_info = extrair_lotes_validade(info_adicional.text if info_adicional is not None else "")
        lotes_validade_rastro = extrair_lotes_rastro(det, ns)
        
        lotes_validade = lotes_validade_rastro + lotes_validade_info
        
        if lotes_validade:
            quantidade_por_lote = quantidade_total // len(lotes_validade)  
            for lote, validade in lotes_validade:
                data.append([num_nota_fiscal, serie_nota_fiscal, natureza_operacao, chave_nota_fiscal, fornecedor, produto, lote, quantidade_por_lote, validade])
        else:
            data.append([num_nota_fiscal, serie_nota_fiscal, natureza_operacao, chave_nota_fiscal, fornecedor, produto, None, quantidade_total, None])
    
    return data

def processar_arquivos_xml(arquivos):
    todas_as_notas = []
    for arquivo in arquivos:
        dados_nota = processar_nfe(arquivo)
        if dados_nota:
            todas_as_notas.extend(dados_nota)
    
    df = pd.DataFrame(todas_as_notas, columns=[
        "NÚMERO DA NOTA FISCAL", "SÉRIE DA NOTA FISCAL", "NATUREZA DE OPERAÇÃO", "CHAVE DA NOTA FISCAL", "FORNECEDOR",
        "PRODUTO", "LOTE", "QUANTIDADE", "VALIDADE"
    ])
    
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
