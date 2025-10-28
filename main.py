import os
from dotenv import load_dotenv
from jira import JIRA
from datetime import datetime
from jira_client import JiraClient, IssueInfo, IssueAnalysis
from typing import List
from llm_client import LLMClient
from business_info import BusinessInfo
from output_manager import OutputManager
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

load_dotenv()

JIRA_SERVER = os.getenv("JIRA_SERVER")
JIRA_USER = os.getenv("JIRA_USER")
JIRA_TOKEN = os.getenv("JIRA_API_TOKEN")
FILTER_ID = os.getenv("JIRA_FILTER_ID")


def main():
    print("Everything OK!")

    # Leer filtro según el código pre definido
    filter = os.getenv("JIRA_FILTER_ID")

    # Buscar información de los issues del filtro
    issues_info = get_issue_list_info(filter)

    # Generar la salida
    create_output_table(issues_info)

    print("Success!!")


def get_issue_list_info(filter) -> List[IssueInfo]:
    '''
    Método para obtener la información de los issues desde un filtro de Jira
    '''

    # Instanciar cliente Jira
    jira_client = JiraClient()
    
    #Obtener los issues desde el filtro
    issues = jira_client.get_issues_from_filter(filter)
    
    # Capturar información de cada uno de los issues
    info = jira_client.proccess_issue_list_info(issues)

    return info


def get_business_info() -> str:
    '''
    Método para obtener la información de negocio relativa a una HU.
    '''
    # Usar cliente de información del negocio (genérico)
    business_info = BusinessInfo()

    # Obtener la información a través de un método del cliente
    info = business_info.get_business_info("GOBI-895")

    # Retornar la información
    return info


# Método "histórico". Ya no estamos usando llamadas directas a un cliente LLM
def test_llm_client():
    '''
    Método para probar hacer un completion genérico con un LLM
    '''

    # Crear el cliente de LLM
    llm_client = LLMClient()

    # Crear el prompt a user
    prompt = "Explica como funciona la API de Jira en Python."
    
    # Generar el texto
    response = llm_client.generate_text(prompt)
    
    # Imprimir la respuesta
    print("LLM Response:")
    print(response)



def create_output_table(issues: List[IssueInfo]) -> None:
    '''
    Método que hace el procesamiento de la información.
    
    Recibe una lista de información de issues. Genera la cadena de consulta y salida.'''

    # Obtener la instancia del OutputManager
    output_manager = OutputManager()

    # Obtener parámetros de configuración
    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("LLM_API_KEY")

    # Crear prompt desde una plantilla. Parametrizado a variables
    prompt = ChatPromptTemplate.from_template("""
    Eres un asistente que resume información de issues de Jira para reportes de negocio.

    Analiza los siguientes datos de un issue:
    - Clave del issue: {key}
    - Resumen original: {summary}
    - Descripción: {description}
    - Documento de valor de negocio: {business_info}

    Genera una respuesta estructurada con los siguientes campos:

    1. "resumen": descripción breve (máximo 10 palabras) que explica de qué se trata el issue.
    2. "valor_negocio": resumen (máximo 25 palabras) del valor de negocio aportado por la HU, usando únicamente la sección de "objetivos de la iniciativa" del documento.
    3. "metrica_impactada": nombre de la métrica más impactada por la HU, sin explicaciones adicionales.
    4. "impactos_globales": el impacto que la HU tiene en todas las métricas definidas en la sección correspondiente, con nivel "Nulo", "Bajo", "Medio" o "Alto".
    5. "justificaciones": la justificación para cada uno de los impactos del punto anterior, con nombre de métrica y justificación
    """)

    llm = ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0
        )
    
    # Crear LLM con salida estructurada. Este paso es crítico.
    # Genera un RunnableBinding que hace un wrapper de LLM comportamiento adicional
    # (en este caso, la capacidad de manejar salida estructurada)
    structured_llm = llm.with_structured_output(IssueAnalysis)

    # La "cadena" de ejecución. De tipo RunnableSequence
    chain = prompt | structured_llm

    # Iterar por cada HU encontrada
    for issue in issues:
        print(f"Procesando issue {issue.key} para tabla de salida...")

        # Crear la estructura de entrada, con los parámetros que espera el prompt
        issue_data ={
            "key": issue.key,
            "summary": issue.summary,
            "description": issue.description,
            "business_info": issue.business_info
        }

        try:
            # Invocar la cadena. Esto genera la ejecución del RunnableSequence. En este caso,
            # el prompt que entra en el LLM con estructura
            result = chain.invoke(issue_data)
            
            # Generar salida especial para la fecha
            release_date = datetime.fromisoformat(issue.resolution_date.replace('Z', '+00:00')).strftime('%d-%m')
            
            # Generar fila para guardar
            row = {
                "HU": issue.key,
                "GOBI": issue.epic_key,
                "Descripción": result.resumen,
                "Fecha de liberación": release_date,
                "Valor de negocio": result.valor_negocio,
                "Métrica impactada": result.metrica_impactada
            }

            # Agregar la fila a la tabla de salida
            output_manager.add_record_to_table(row)

            # Convertir la respuesta del LLM en reporte (para archivo de texto)
            report = result.to_text_report(issue.key)

            # Guardar archivo de texto
            output_manager.save_output_to_text(issue.key, report)

            # Generar lista de impactos con formato de dict
            impact_list = output_manager.obtain_impact_list(result.impactos_globales)

            # Guardar impactos en gráficos
            output_manager.create_visual_output(issue.key, impact_list)


        except Exception as e:
            print(f"Error al procesar el issue {issue.key}: {e}")
            continue
    
    output_manager.save_table_to_csv("output_table.csv")



if __name__ == "__main__":
    main()