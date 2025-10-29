import os
from dotenv import load_dotenv
from jira import JIRA
from typing import List
from business_info import BusinessInfo
from pydantic import BaseModel, Field

load_dotenv

class IssueInfo:
    def __init__(
            self,
            key,
            summary,
            description,
            resolution_date,
            business_info = None,
            epic_key = None,
            epic_summary = None):
        self.key = key
        self.summary = summary
        self.description = description
        self.resolution_date = resolution_date
        self.business_info = business_info
        self.epic_key = epic_key
        self.epic_summary = epic_summary
    

    def __repr__(self):
        return (f"IssueInfo(key={self.key}, summary={self.summary!r}, "
                f"epic_key={self.epic_key}, resolved={self.resolution_date})")


class IssueAnalysis(BaseModel):
    issue_key: str = Field(..., description="La clave del issue de Jira (e.g, SVA-1000)")
    epic_key: str = Field(..., description="La clave de la épica del issue de Jira (e.g., GOBI-800)")
    resolution_date: str = Field(..., description="La fecha de resolución del issue de Jira, expresado en formato MM-DD")
    resumen: str = Field(..., description="Descripción de máximo 10 palabras del issue")
    valor_negocio: str = Field(..., description="Resumen de máximo 25 palabras del valor de negocio de la HU, considerando sólo objetivos de la iniciativa.")
    metrica_impactada: str = Field(..., description="Nombre de la métrica principal impactada por la HU.")
    impactos_globales: str = Field(..., description="Lista del nivel de impacto en todas las métricas")
    justificaciones: str = Field(..., description="Justificaciones para los impactos de cada métrica")


    def to_text_report(self, issue_key: str) -> str:
        """
        Crea una representación en texto plano y formateada de los resultados del análisis.

        Args:
            issue_key: La clave del issue (e.g., "PROJ-123") para incluir en el reporte.

        Returns:
            Una cadena de texto formateada para el reporte.
        """
        report = f"""
        ==================================================
                REPORTE DE ANÁLISIS DE ISSUE: {issue_key}
        ==================================================

        Resumen Breve:
        {self.resumen}

        Valor de Negocio:
        {self.valor_negocio}

        Métrica Principal Impactada:
        {self.metrica_impactada}

        --- Detalles del Impacto ---

        Impactos Globales (Niveles):
        {self.impactos_globales}

        Justificaciones de Impacto:
        {self.justificaciones}

        ==================================================
        """
        return report.strip()


class JiraClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(JiraClient, cls).__new__(cls)
            cls._instance._init_client()
        return cls._instance
    
    def _init_client(self):
        server = os.getenv("JIRA_SERVER")
        user = os.getenv("JIRA_USER")
        token = os.getenv("JIRA_API_TOKEN")
        options = {"server": server}
        self.client = JIRA(options, basic_auth=(user, token))


    def get_issues_from_filter(self, filter_id):
        '''Método para traer los issues contenidos en algún filtro, a través de la API de Jira.
        '''
        
        print(f"Fetching all issues from Jira filter {filter_id}")
        
        # Obtiene toda la información de los issues directo desde Jira
        # Clase Issue de la librería de Jira
        issues = self.client.search_issues(f"filter={filter_id}", maxResults=False)
        
        # Informar y retonar issues
        print(f"Found {len(issues)} issues.")
        return issues
    
    
    def proccess_issue_list_info(self, issues) -> List[IssueInfo]:
        '''Método para obtener la información de cada HU dentro de una lista.
        '''
        
        # Colección para información de HUs.
        info_collection = []

        # Por cada HU dentro de la lista original
        for issue in issues:

            # Leer información de la HU desde la API de Jira
            issue_info = self._get_issue_info(issue)

            # Agregar a la colección
            info_collection.append(issue_info)

        # Retornar la colección
        return info_collection
    

    def _get_issue_info(self, issue) -> IssueInfo:
        '''
        Método para obtener la información de un issue a través de la API de Jira
        
        Recibe el issue desde la clase de la librería de Jira y lo transforma en la estructura
        de IssueInfo, que es la que contiene lo necesario para este análisis.'''

        issue_key = issue.key
        summary = issue.fields.summary
        description = issue.fields.description
        resolution_date = issue.fields.resolutiondate or "not resolved"
        epic_key = issue.fields.parent.key
        epic_summary = None

        # Agregar información de business info si existe
        # En esta versión, busca directo en la épica
        business_info = BusinessInfo()

        # Si hay una épica asociada
        if epic_key:

            # Validar si ya fue leído si archivo
            exists = business_info.epic_already_read(epic_key)
            
            # Si no ha sido leído
            if not exists:
                # Leer el archivo desde Jira y asignar a la info de negocios
                info = self.get_epic_info(epic_key)
                
                # Agregar a la lista de contextos de negocios ya encontrados, para no tener
                # que hacer la consulta de nuevo si aparece otra HU relacionada
                business_info.add_epic_to_list(epic_key, info)

            else:
                # Obtener del contexto ya cargado para esta épica
                info = business_info.get_epic_from_list(epic_key)

        # Retornar la clase con todos los detalles, incluyendo el contexto de negocios
        return IssueInfo(
            key=issue_key,
            summary=summary,
            description=description,
            resolution_date=resolution_date,
            business_info=info,
            epic_key=epic_key,
            epic_summary=epic_summary
        )
    

    def get_epic_info(self, epic_key: str) -> str:

        try:
            # Buscar la información de la épica
            epic_issue = self.client.issue(epic_key)

            # Adjuntar extensión al nombre del archivo
            filename = epic_key + ".txt"

            # Iterar en los adjuntos obtenidos de la épica
            for attachment in epic_issue.fields.attachment:

                # Si el nombre del archivo buscado corresponde al attachment, leerlo
                if filename.lower() in attachment.filename.lower():
                    file_content = attachment.get()
                    print(f"Detalles de la iniciativa de negocios encontrados en {epic_key}")
                    return file_content.decode('utf-8')
                
            return f"Archivo de información de negocio {filename} no encontrado"
            
        except Exception as e:
            return f"Error al intentar obtener información de negocios para épica {epic_key}: {str(e)}"
        


