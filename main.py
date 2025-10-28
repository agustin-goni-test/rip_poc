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

    # test_llm_client()

    # Leer filtro según el código pre definido
    filter = os.getenv("JIRA_FILTER_ID")

    # Buscar información de los issues del filtro
    issues_info = get_issue_list_info(filter)

    # Usar la información de los issues para obtener detalles de cada caso
    # for issue in issues_info:
    #     # Obtener el valor del issue cerrado
    #     valor = obtain_value_for_issue(issue)

    #     # Guardar el valor por HU
    #     save_issue_value(issue.key, valor)


    create_output_table(issues_info)

    # # issue = issues_info[0]
    # for issue in issues_info:
    #     valor = obtener_valor_para_una_hu(issue, info)

    #     guardar_valor_por_hu(issue.key, valor)

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
    # Usar cliente de información del negocio (genérico)
    business_info = BusinessInfo()

    # Obtener la información a través de un método del cliente
    info = business_info.get_business_info("GOBI-895")

    # Retornar la información
    return info


def test_llm_client():
    '''
    Método para probar hacer un completion genérico con un LLM'''

    # Crear el cliente de LLM
    llm_client = LLMClient()

    # Crear el prompt a user
    prompt = "Explica como funciona la API de Jira en Python."
    
    # Generar el texto
    response = llm_client.generate_text(prompt)
    
    # Imprimir la respuesta
    print("LLM Response:")
    print(response)


# def obtain_value_for_issue(issue: IssueInfo) -> str:
#     '''
#     Método para obtener el valor de una HU específica
#     '''

#     print(f"\nObteniendo valor de negocio para la HU {issue.key}, de GOBI {issue.epic_key}...")

#     # Crear el cliente de LLM
#     llm_client = LLMClient()

#     # Obtener información para el prompt
#     key = issue.key
#     summary = issue.summary
#     description = issue.description
#     info = issue.business_info

#     # Crear prompt que ponga en contexto el modelo
#     prompt = f"""
#     Tengo un issue de Jira ya cerrado con clave {key}, con título {summary} y con esta descripción: ''' {description} '''.
#     Quiero extraer el valor de negocio asociado a la HU. Para eso, cuento con la siguiente descripción
#     del valor de negocio de la inciativa en la que se encaja: ''' {info} '''. Para esto, recorre cada una
#     de las métricas definidas en la información del negocio y explicar si la HU contribuye a mejorar esa métrica.
#     Categoriza el impacto que pueda tener sobre cada métrica en "Alto", "Medio", "Bajo" o "Nulo", e indica 
#     brevemente por qué. Finalmente, entrega un resumen del valor de negocio total que aporta la HU, donde indiques
#     cuál de las métricas es la más impactada (sólo puede ser una de las que existan, la más relevante). Acá incluye
#     solamente el nombre de la métrica y nada más.
#     Entrega la respuesta la medición de impactos y las justificaciones en secciones "IMPACTOS" y "JUSTIFICACIONES", y "RESUMEN".
#     Por lo tanto, la respuesta debe ordenarse así: 1) IDENTIFICACIÓN del issue (su key); 2) IMPACTOS; 3) JUSTIFICACIONES; 4)RESUMEN.
#     Entrega una salida de texto plano, sin formatos.    
#     """

#     response = llm_client.generate_text(prompt)

#     print(f"\n\nValor de negocio para la HU {key}:\n")
#     print(response)

#     return response


# def save_issue_value(issue_key: str, valor: str) -> None:
#     '''
#     Método para guardar el valor de negocio de una HU en un archivo de texto
#     '''

#     print(f"\nGuardando valor de negocio para la HU {issue_key}...")

#     # Crear el gestor de salida
#     output_manager = OutputManager()

#     # Guardar el valor en un archivo de texto
#     output_manager.save_output_to_text(issue_key, valor)

#     impact_list = output_manager.obtain_impact_list(valor)

#     output_manager.create_visual_output(issue_key, impact_list)

#     return None


def create_output_table(issues: List[IssueInfo]) -> None:

    # Obtener la instancia del OutputManager
    output_manager = OutputManager()

    model = os.getenv("LLM_MODEL", "deepseek-chat")
    api_key = os.getenv("LLM_API_KEY")
    # api_key = "AIzaSyA2P24LFUoyF4yO4v92BHHvxwfSAdEzt1o"
    api_base_url = os.getenv("LLM_API_BASE_URL")

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
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0
        )
    
    structured_llm = llm.with_structured_output(IssueAnalysis)
    chain = prompt | structured_llm

    # chain = llm.with_structured_output(IssueAnalysis, prompt=prompt)

    for issue in issues:
        print(f"Procesando issue {issue.key} para tabla de salida...")

        issue_data ={
            "key": issue.key,
            "summary": issue.summary,
            "description": issue.description,
            "business_info": issue.business_info
        }

        try:
            result = chain.invoke(issue_data)
            release_date = datetime.fromisoformat(issue.resolution_date.replace('Z', '+00:00')).strftime('%d-%m')
            
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


# def validate_summary(issue: IssueInfo) -> str:
#     '''
#     Método para asegurar que exista un resumen adecuado para el issue
#     '''
#     print(f"Elaborando resumen para el issue {issue.key}...")

#     llm_client = LLMClient()

#     original_summary = issue.summary
#     description = issue.description

#     prompt = f"""
#     Considerando este resumen: {original_summary} y esta descripción: {description},
#     entrega una descripción de máximo 10 palabras para explicar de que se trata el issue.
#     """

#     response = llm_client.generate_text(prompt)
#     return response


# def get_business_value(issue: IssueInfo, info: BusinessInfo) -> str:
#     '''
#     Método para obtener el valor de negocio resumido de una HU
#     '''
#     print(f"Obteniendo valor de negocio resumido para la HU {issue.key}...")

#     # Obtener el cliente de LLM
#     llm_client = LLMClient()

#     summary = issue.summary
#     description = issue.description

#     prompt = f"""
#     Considerando un issue con este resumen: ''' {summary} ''' esta descripción: ''' {description} ''', y
#     teniendo como referencia este documento de valor de negocio: ''' {info} ''',
#     quiero un resumen de no más de 25 palabras respecto a cuál es el valor de negocio que aporta esta HU.
#     Para obtenerlo considera solamente la sección de los objetivos de la iniciativa, no las métricas.
#     Evita mantener problemas gramaticales en la respuesta. Por ejemplo, si en el issue dice ''' Listado Comercios '''
#     (con mayúsculas), escribe la respuesta con minúsculas: ''' listado comercios '''.
#     """

#     response = llm_client.generate_text(prompt)
#     return response


# def get_main_metric(issue: IssueInfo, info: BusinessInfo) -> str:
#     '''
#     Método para obtener la métrica más impactada por una HU
#     '''
#     print(f"Obteniendo métrica más impactada para la HU {issue.key}...")

#     # Obtener el cliente de LLM
#     llm_client = LLMClient()

#     summary = issue.summary
#     description = issue.description

#     prompt = f"""
#     Considerando un issue con este resumen: ''' {summary} ''' esta descripción: ''' {description} ''', y
#     teniendo como referencia este documento de valor de negocio: ''' {info} ''',
#     quiero que me indiques cuál es la métrica más impactada por esta HU.
#     Responde solamente con el nombre de la métrica, sin explicaciones adicionales.
#     """

#     response = llm_client.generate_text(prompt)
#     return response


if __name__ == "__main__":
    main()