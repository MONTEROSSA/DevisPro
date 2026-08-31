#!/usr/bin/env python3
"""
ERP-Ökosystem für DevisPro
Plugin-Schnittstellen für Abacus, Proffix, SAP, Microsoft Dynamics, Oracle, DATEV
Offline-First: Lokale Zwischenspeicherung + optionaler Sync zur ERP-API
"""

import json
import os
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod
import urllib.request
import urllib.error


class ERPType(Enum):
    """Unterstützte ERP-Systeme"""
    ABACUS = "Abacus"
    PROFFIX = "Proffix"
    SAP = "SAP"
    DYNAMICS = "Microsoft Dynamics"
    ORACLE = "Oracle"
    DATEV = "DATEV"
    CUSTOM = "Custom"


class SyncDirection(Enum):
    """Sync-Richtung"""
    IMPORT = "Import (ERP → DevisPro)"
    EXPORT = "Export (DevisPro → ERP)"
    BIDIRECTIONAL = "Bidirektional"


@dataclass
class ERPConfig:
    """Konfiguration für ein ERP-System"""
    name: str
    erp_type: str
    api_url: str = ""
    api_key: str = ""
    api_secret: str = ""
    company_id: str = ""
    project_id: str = ""
    username: str = ""
    password: str = ""
    sync_direction: str = "Bidirektional"
    sync_interval_minutes: int = 30
    enabled: bool = True
    auto_sync: bool = False
    field_mapping: Dict = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ERPCredential:
    """ERP-Zugangsdaten (verschlüsselt gespeichert)"""
    name: str
    erp_type: str
    encrypted_data: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ERPProject:
    """Ein ERP-Projekt / Auftrag"""
    erp_id: str
    erp_type: str
    project_number: str
    project_name: str
    customer_name: str = ""
    customer_email: str = ""
    customer_phone: str = ""
    address: str = ""
    city: str = ""
    zip_code: str = ""
    country: str = "Schweiz"
    description: str = ""
    status: str = "active"
    start_date: str = ""
    end_date: str = ""
    budget: float = 0.0
    currency: str = "CHF"
    positions: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)


@dataclass
class ERPCustomer:
    """Ein ERP-Kunde"""
    erp_id: str
    erp_type: str
    customer_number: str
    name: str
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    zip_code: str = ""
    country: str = "Schweiz"
    vat_id: str = ""
    payment_terms: str = ""
    metadata: Dict = field(default_factory=dict)


class ERPPlugin(ABC):
    """Basis-Klasse für ERP-Plugins"""

    def __init__(self, config: ERPConfig):
        self.config = config
        self._cache_dir = Path("erp_cache") / config.name
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def test_connection(self) -> Dict:
        """Testet die ERP-Verbindung"""
        pass

    @abstractmethod
    def import_projects(self) -> List[ERPProject]:
        """Importiert Projekte aus dem ERP"""
        pass

    @abstractmethod
    def export_project(self, project: ERPProject) -> Dict:
        """Exportiert ein Projekt ins ERP"""
        pass

    @abstractmethod
    def import_customers(self) -> List[ERPCustomer]:
        """Importiert Kunden aus dem ERP"""
        pass

    def _api_request(self, method: str, endpoint: str, data: Dict = None, headers: Dict = None) -> Dict:
        """Allgemeiner API-Request (offline-tolerant)"""
        url = f"{self.config.api_url.rstrip('/')}/{endpoint.lstrip('/')}"
        req_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        if self.config.api_key:
            req_headers["Authorization"] = f"Bearer {self.config.api_key}"
        if headers:
            req_headers.update(headers)

        payload = json.dumps(data).encode("utf-8") if data else None
        req = urllib.request.Request(url, data=payload, headers=req_headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.reason}"}
        except urllib.error.URLError as e:
            return {"error": f"URL Error: {str(e)}"}
        except Exception as e:
            return {"error": f"Request Error: {str(e)}"}

    def _cache_get(self, key: str) -> Optional[Dict]:
        """Liest aus lokalem Cache"""
        cache_file = self._cache_dir / f"{key}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _cache_set(self, key: str, data: Dict):
        """Schreibt in lokalen Cache"""
        cache_file = self._cache_dir / f"{key}.json"
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _cache_list(self) -> Dict:
        """Listet alle Cache-Einträge"""
        result = {}
        for cache_file in self._cache_dir.glob("*.json"):
            key = cache_file.stem
            with open(cache_file, "r", encoding="utf-8") as f:
                result[key] = json.load(f)
        return result


class AbacusPlugin(ERPPlugin):
    """Abacus ERP Plugin"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", "/api/v1/info")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v1/projects")
            if "error" not in result:
                projects = []
                for item in result.get("projects", []):
                    project = ERPProject(
                        erp_id=str(item.get("id", "")),
                        erp_type=ERPType.ABACUS.value,
                        project_number=item.get("number", ""),
                        project_name=item.get("name", ""),
                        customer_name=item.get("customer", {}).get("name", ""),
                        customer_email=item.get("customer", {}).get("email", ""),
                        address=item.get("address", ""),
                        city=item.get("city", ""),
                        zip_code=item.get("zip", ""),
                        description=item.get("description", ""),
                        status=item.get("status", "active"),
                        start_date=item.get("start_date", ""),
                        end_date=item.get("end_date", ""),
                        budget=float(item.get("budget", 0)),
                        currency=item.get("currency", "CHF"),
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        # Fallback auf Cache
        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", "/api/v1/projects", data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True, "message": "Offline gespeichert"}

    def import_customers(self) -> List[ERPCustomer]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v1/customers")
            if "error" not in result:
                customers = []
                for item in result.get("customers", []):
                    customer = ERPCustomer(
                        erp_id=str(item.get("id", "")),
                        erp_type=ERPType.ABACUS.value,
                        customer_number=item.get("number", ""),
                        name=item.get("name", ""),
                        email=item.get("email", ""),
                        phone=item.get("phone", ""),
                        address=item.get("address", ""),
                        city=item.get("city", ""),
                        zip_code=item.get("zip", ""),
                        country=item.get("country", "Schweiz"),
                        vat_id=item.get("vat_id", ""),
                        payment_terms=item.get("payment_terms", ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


class ProffixPlugin(ERPPlugin):
    """Proffix ERP Plugin"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", "/api/v1/info")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v1/projekte")
            if "error" not in result:
                projects = []
                for item in result.get("projects", result.get("data", [])):
                    project = ERPProject(
                        erp_id=str(item.get("ProjektID", item.get("id", ""))),
                        erp_type=ERPType.PROFFIX.value,
                        project_number=item.get("ProjektNr", item.get("number", "")),
                        project_name=item.get("ProjektName", item.get("name", "")),
                        customer_name=item.get("Kunde", {}).get("Name", item.get("customer", "")),
                        customer_email=item.get("Kunde", {}).get("Email", ""),
                        address=item.get("Adresse", item.get("address", "")),
                        city=item.get("Ort", item.get("city", "")),
                        zip_code=item.get("PLZ", item.get("zip", "")),
                        description=item.get("Beschreibung", item.get("description", "")),
                        status=item.get("Status", "active"),
                        budget=float(item.get("Budget", 0)),
                        currency="CHF",
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", "/api/v1/projekte", data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True}

    def import_customers(self) -> List[ERPCustomer]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v1/kunden")
            if "error" not in result:
                customers = []
                for item in result.get("customers", result.get("data", [])):
                    customer = ERPCustomer(
                        erp_id=str(item.get("KundenID", item.get("id", ""))),
                        erp_type=ERPType.PROFFIX.value,
                        customer_number=item.get("KundenNr", item.get("number", "")),
                        name=item.get("Name", item.get("name", "")),
                        email=item.get("Email", ""),
                        phone=item.get("Telefon", ""),
                        address=item.get("Adresse", ""),
                        city=item.get("Ort", ""),
                        zip_code=item.get("PLZ", ""),
                        country=item.get("Land", "Schweiz"),
                        vat_id=item.get("MWSTNr", ""),
                        payment_terms=item.get("Zahlungsbedingungen", ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


class SAPPlugin(ERPPlugin):
    """SAP ERP Plugin"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", "/sap/bc/api/v1/info")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        if self.config.api_url:
            result = self._api_request("GET", "/sap/bc/api/v1/projects")
            if "error" not in result:
                projects = []
                for item in result.get("d", {}).get("results", []):
                    project = ERPProject(
                        erp_id=str(item.get("ProjectID", "")),
                        erp_type=ERPType.SAP.value,
                        project_number=item.get("ProjectNumber", ""),
                        project_name=item.get("ProjectName", ""),
                        customer_name=item.get("CustomerName", ""),
                        customer_email=item.get("CustomerEmail", ""),
                        address=item.get("Address", ""),
                        city=item.get("City", ""),
                        zip_code=item.get("PostalCode", ""),
                        description=item.get("Description", ""),
                        status=item.get("Status", "active"),
                        start_date=item.get("StartDate", ""),
                        end_date=item.get("EndDate", ""),
                        budget=float(item.get("Budget", 0)),
                        currency=item.get("Currency", "CHF"),
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", "/sap/bc/api/v1/projects", data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True}

    def import_customers(self) -> List[ERPCustomer]:
        if self.config.api_url:
            result = self._api_request("GET", "/sap/bc/api/v1/customers")
            if "error" not in result:
                customers = []
                for item in result.get("d", {}).get("results", []):
                    customer = ERPCustomer(
                        erp_id=str(item.get("CustomerID", "")),
                        erp_type=ERPType.SAP.value,
                        customer_number=item.get("CustomerNumber", ""),
                        name=item.get("Name", ""),
                        email=item.get("Email", ""),
                        phone=item.get("Phone", ""),
                        address=item.get("Address", ""),
                        city=item.get("City", ""),
                        zip_code=item.get("PostalCode", ""),
                        country=item.get("Country", "Schweiz"),
                        vat_id=item.get("VATID", ""),
                        payment_terms=item.get("PaymentTerms", ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


class DynamicsPlugin(ERPPlugin):
    """Microsoft Dynamics 365 ERP Plugin"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", "/api/data/v9.2/WhoAmI")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/data/v9.2/projects")
            if "error" not in result:
                projects = []
                for item in result.get("value", []):
                    project = ERPProject(
                        erp_id=str(item.get("projectid", item.get("id", ""))),
                        erp_type=ERPType.DYNAMICS.value,
                        project_number=item.get("projectnumber", item.get("msdyn_projectnumber", "")),
                        project_name=item.get("name", ""),
                        customer_name=item.get("_customerid_value", item.get("customer", "")),
                        description=item.get("description", ""),
                        status=item.get("statuscode", "active"),
                        start_date=item.get("msdyn_startdate", ""),
                        end_date=item.get("msdyn_finishdate", ""),
                        budget=float(item.get("msdyn_totalcost", 0)),
                        currency=item.get("transactioncurrencyid", "CHF"),
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", "/api/data/v9.2/projects", data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True}

    def import_customers(self) -> List[ERPCustomer]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/data/v9.2/accounts?$filter=accountcategorycode eq 'Customer'")
            if "error" not in result:
                customers = []
                for item in result.get("value", []):
                    customer = ERPCustomer(
                        erp_id=str(item.get("accountid", item.get("id", ""))),
                        erp_type=ERPType.DYNAMICS.value,
                        customer_number=item.get("accountnumber", ""),
                        name=item.get("name", ""),
                        email=item.get("emailaddress1", ""),
                        phone=item.get("telephone1", ""),
                        address=item.get("address1_line1", ""),
                        city=item.get("address1_city", ""),
                        zip_code=item.get("address1_postalcode", ""),
                        country=item.get("address1_country", "Schweiz"),
                        vat_id=item.get("vatnumber", ""),
                        payment_terms=item.get("paymenttermscode", ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


class DATEVPlugin(ERPPlugin):
    """DATEV ERP Plugin (Deutschland-spezifisch)"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", "/api/v2/info")
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v2/projects")
            if "error" not in result:
                projects = []
                for item in result.get("projects", []):
                    project = ERPProject(
                        erp_id=str(item.get("id", "")),
                        erp_type=ERPType.DATEV.value,
                        project_number=item.get("project_number", ""),
                        project_name=item.get("name", ""),
                        customer_name=item.get("customer_name", ""),
                        customer_email=item.get("customer_email", ""),
                        address=item.get("address", ""),
                        city=item.get("city", ""),
                        zip_code=item.get("zip", ""),
                        country="Deutschland",
                        description=item.get("description", ""),
                        status=item.get("status", "active"),
                        budget=float(item.get("budget", 0)),
                        currency="EUR",
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", "/api/v2/projects", data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True}

    def import_customers(self) -> List[ERPCustomer]:
        if self.config.api_url:
            result = self._api_request("GET", "/api/v2/contacts")
            if "error" not in result:
                customers = []
                for item in result.get("contacts", []):
                    customer = ERPCustomer(
                        erp_id=str(item.get("id", "")),
                        erp_type=ERPType.DATEV.value,
                        customer_number=item.get("number", ""),
                        name=item.get("name", ""),
                        email=item.get("email", ""),
                        phone=item.get("phone", ""),
                        address=item.get("address", ""),
                        city=item.get("city", ""),
                        zip_code=item.get("zip", ""),
                        country="Deutschland",
                        vat_id=item.get("vat_id", ""),
                        payment_terms=item.get("payment_terms", ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


class CustomPlugin(ERPPlugin):
    """Custom/Generisches ERP Plugin (REST API)"""

    def test_connection(self) -> Dict:
        if not self.config.api_url:
            return {"success": False, "error": "Keine API-URL konfiguriert"}
        result = self._api_request("GET", self.config.metadata.get("health_endpoint", "/health"))
        if "error" in result:
            return {"success": False, "error": result["error"]}
        return {"success": True, "info": result}

    def import_projects(self) -> List[ERPProject]:
        endpoint = self.config.metadata.get("projects_endpoint", "/projects")
        if self.config.api_url:
            result = self._api_request("GET", endpoint)
            if "error" not in result:
                projects = []
                items = result if isinstance(result, list) else result.get("projects", result.get("data", []))
                for item in items:
                    field_map = self.config.field_mapping.get("project", {})
                    project = ERPProject(
                        erp_id=str(item.get(field_map.get("id", "id"), "")),
                        erp_type=ERPType.CUSTOM.value,
                        project_number=item.get(field_map.get("number", "number"), ""),
                        project_name=item.get(field_map.get("name", "name"), ""),
                        customer_name=item.get(field_map.get("customer", "customer"), ""),
                        description=item.get(field_map.get("description", "description"), ""),
                        status=item.get(field_map.get("status", "status"), "active"),
                        budget=float(item.get(field_map.get("budget", "budget"), 0)),
                        currency=item.get(field_map.get("currency", "currency"), "CHF"),
                    )
                    projects.append(project)
                self._cache_set("projects", [asdict(p) for p in projects])
                return projects

        cached = self._cache_get("projects")
        if cached:
            return [ERPProject(**p) for p in cached]
        return []

    def export_project(self, project: ERPProject) -> Dict:
        endpoint = self.config.metadata.get("projects_endpoint", "/projects")
        data = asdict(project)
        if self.config.api_url:
            result = self._api_request("POST", endpoint, data=data)
            if "error" in result:
                return {"success": False, "error": result["error"]}
            return {"success": True, "result": result}
        self._cache_set(f"export_{project.erp_id}", data)
        return {"success": True, "cached": True}

    def import_customers(self) -> List[ERPCustomer]:
        endpoint = self.config.metadata.get("customers_endpoint", "/customers")
        if self.config.api_url:
            result = self._api_request("GET", endpoint)
            if "error" not in result:
                customers = []
                items = result if isinstance(result, list) else result.get("customers", result.get("data", []))
                for item in items:
                    field_map = self.config.field_mapping.get("customer", {})
                    customer = ERPCustomer(
                        erp_id=str(item.get(field_map.get("id", "id"), "")),
                        erp_type=ERPType.CUSTOM.value,
                        customer_number=item.get(field_map.get("number", "number"), ""),
                        name=item.get(field_map.get("name", "name"), ""),
                        email=item.get(field_map.get("email", "email"), ""),
                        phone=item.get(field_map.get("phone", "phone"), ""),
                        address=item.get(field_map.get("address", "address"), ""),
                        city=item.get(field_map.get("city", "city"), ""),
                        zip_code=item.get(field_map.get("zip", "zip"), ""),
                        country=item.get(field_map.get("country", "country"), "Schweiz"),
                        vat_id=item.get(field_map.get("vat_id", "vat_id"), ""),
                        payment_terms=item.get(field_map.get("payment_terms", "payment_terms"), ""),
                    )
                    customers.append(customer)
                self._cache_set("customers", [asdict(c) for c in customers])
                return customers

        cached = self._cache_get("customers")
        if cached:
            return [ERPCustomer(**c) for c in cached]
        return []


# Plugin-Registry
ERP_PLUGIN_REGISTRY = {
    ERPType.ABACUS.value: AbacusPlugin,
    ERPType.PROFFIX.value: ProffixPlugin,
    ERPType.SAP.value: SAPPlugin,
    ERPType.DYNAMICS.value: DynamicsPlugin,
    ERPType.ORACLE.value: CustomPlugin,  # Oracle nutzt Custom mit Field-Mapping
    ERPType.DATEV.value: DATEVPlugin,
    ERPType.CUSTOM.value: CustomPlugin,
}


class ERPManager:
    """Zentrale ERP-Verwaltung"""

    def __init__(self, config_dir: str = "erp_configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        self.plugins: Dict[str, ERPPlugin] = {}
        self.configs: Dict[str, ERPConfig] = {}
        self._load_configs()

    def _load_configs(self):
        config_file = self.config_dir / "erp_configs.json"
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for name, cfg_data in data.get("configs", {}).items():
                    config = ERPConfig(**cfg_data)
                    self.configs[name] = config
                    self._create_plugin(name, config)

    def _save_configs(self):
        config_file = self.config_dir / "erp_configs.json"
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "configs": {name: self._serialize_config(cfg) for name, cfg in self.configs.items()}
        }
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _serialize_config(self, cfg) -> dict:
        """Konvertiert ERPConfig zu JSON-kompatiblem dict (Enums → Strings)."""
        d = asdict(cfg)
        if hasattr(d.get('erp_type'), 'value'):
            d['erp_type'] = d['erp_type'].value
        if hasattr(d.get('sync_direction'), 'value'):
            d['sync_direction'] = d['sync_direction'].value
        return d

    def _create_plugin(self, name: str, config: ERPConfig):
        plugin_class = ERP_PLUGIN_REGISTRY.get(config.erp_type, CustomPlugin)
        self.plugins[name] = plugin_class(config)

    def add_config(self, name: str, config: ERPConfig):
        self.configs[name] = config
        self._create_plugin(name, config)
        self._save_configs()

    def remove_config(self, name: str):
        if name in self.plugins:
            del self.plugins[name]
        if name in self.configs:
            del self.configs[name]
        self._save_configs()

    def get_plugin(self, name: str) -> Optional[ERPPlugin]:
        return self.plugins.get(name)

    def list_plugins(self) -> Dict[str, Dict]:
        return {
            name: {
                "erp_type": cfg.erp_type,
                "api_url": cfg.api_url,
                "enabled": cfg.enabled,
                "auto_sync": cfg.auto_sync,
                "sync_direction": cfg.sync_direction,
                "company_id": cfg.company_id,
            }
            for name, cfg in self.configs.items()
        }

    def test_all(self) -> Dict[str, Dict]:
        results = {}
        for name, plugin in self.plugins.items():
            if self.configs[name].enabled:
                results[name] = plugin.test_connection()
            else:
                results[name] = {"success": False, "error": "Deaktiviert"}
        return results

    def import_all_projects(self) -> Dict[str, List[ERPProject]]:
        results = {}
        for name, plugin in self.plugins.items():
            if self.configs[name].enabled and self.configs[name].sync_direction in ("Import (ERP → DevisPro)", "Bidirektional"):
                results[name] = plugin.import_projects()
        return results

    def export_project(self, erp_name: str, project: ERPProject) -> Dict:
        plugin = self.get_plugin(erp_name)
        if not plugin:
            return {"success": False, "error": f"ERP '{erp_name}' nicht gefunden"}
        if self.configs[erp_name].sync_direction not in ("Export (DevisPro → ERP)", "Bidirektional"):
            return {"success": False, "error": "Sync-Richtung erlaubt keinen Export"}
        return plugin.export_project(project)

    def import_all_customers(self) -> Dict[str, List[ERPCustomer]]:
        results = {}
        for name, plugin in self.plugins.items():
            if self.configs[name].enabled and self.configs[name].sync_direction in ("Import (ERP → DevisPro)", "Bidirektional"):
                results[name] = plugin.import_customers()
        return results

    def show_gui(self):
        """Zeigt ERP-Verwaltungs-GUI"""
        import tkinter as tk
        from tkinter import ttk, messagebox, filedialog

        win = tk.Toplevel()
        win.title("ERP-Ökosystem")
        win.geometry("1000x700")

        # Toolbar
        toolbar = tk.Frame(win)
        toolbar.pack(fill="x", padx=8, pady=8)

        tk.Button(toolbar, text="ERP hinzufügen", command=self._add_erp_gui,
                  bg="darkgreen", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Alle testen", command=self._test_all_gui,
                  bg="darkblue", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Projekte importieren", command=self._import_projects_gui,
                  bg="darkorange", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Kunden importieren", command=self._import_customers_gui,
                  bg="purple", fg="white").pack(side="left", padx=4)
        tk.Button(toolbar, text="Aktualisieren", command=self._refresh_erp_gui,
                  bg="gray").pack(side="left", padx=4)

        # Status
        status_frame = tk.Frame(win)
        status_frame.pack(fill="x", padx=8, pady=(0, 8))
        self._erp_status_label = tk.Label(status_frame, text="Status: Bereit", anchor="w")
        self._erp_status_label.pack(side="left", fill="x", expand=True)

        # ERP-Liste (Treeview)
        tree_frame = tk.LabelFrame(win, text="ERP-Systeme")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=4)

        cols = ("name", "erp_type", "api_url", "enabled", "auto_sync", "sync_direction", "status")
        tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=10)
        tree.heading("name", text="Name")
        tree.heading("erp_type", text="ERP-Typ")
        tree.heading("api_url", text="API-URL")
        tree.heading("enabled", text="Aktiv")
        tree.heading("auto_sync", text="Auto")
        tree.heading("sync_direction", text="Sync-Richtung")
        tree.heading("status", text="Status")
        tree.column("name", width=120)
        tree.column("erp_type", width=120)
        tree.column("api_url", width=250)
        tree.column("enabled", width=50, anchor="center")
        tree.column("auto_sync", width=50, anchor="center")
        tree.column("sync_direction", width=150)
        tree.column("status", width=80, anchor="center")
        tree.pack(fill="both", expand=True, padx=4, pady=4)

        def on_double_click(event):
            selection = tree.selection()
            if selection:
                name = tree.item(selection[0])['tags'][0]
                self._edit_erp_gui(name)

        tree.bind("<Double-1>", on_double_click)
        self._erp_tree = tree

        # Detail-Bereich
        detail_frame = tk.LabelFrame(win, text="Details")
        detail_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self._erp_detail = tk.Text(detail_frame, height=8, wrap="word", font=("Courier", 9))
        self._erp_detail.pack(fill="both", expand=True, padx=4, pady=4)
        self._erp_detail.config(state="disabled")

        # Buttons
        btn_frame = tk.Frame(win)
        btn_frame.pack(fill="x", padx=8, pady=8)
        tk.Button(btn_frame, text="Bearbeiten", command=lambda: self._edit_erp_gui_selected(tree)).pack(side="left", padx=4)
        tk.Button(btn_frame, text="Löschen", command=lambda: self._delete_erp_gui_selected(tree), bg="darkred", fg="white").pack(side="left", padx=4)
        tk.Button(btn_frame, text="Testen", command=lambda: self._test_erp_gui_selected(tree)).pack(side="left", padx=4)

        self._refresh_erp_gui()

    def _refresh_erp_gui(self):
        if not hasattr(self, "_erp_tree"):
            return
        tree = self._erp_tree
        tree.delete(*tree.get_children())
        for name, cfg in self.configs.items():
            tree.insert("", "end", values=(
                name,
                cfg.erp_type,
                cfg.api_url or "(offline)",
                "✓" if cfg.enabled else "✗",
                "✓" if cfg.auto_sync else "✗",
                cfg.sync_direction,
                "Aktiv" if cfg.enabled else "Inaktiv"
            ), tags=(name,))

    def _add_erp_gui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox

        win = tk.Toplevel()
        win.title("Neues ERP-System hinzufügen")
        win.geometry("700x600")

        fields = {}

        tk.Label(win, text="Name:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        fields["name"] = tk.Entry(win, width=50)
        fields["name"].grid(row=0, column=1, padx=8, pady=4, sticky="ew")

        tk.Label(win, text="ERP-Typ:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        fields["erp_type"] = ttk.Combobox(win, values=[t.value for t in ERPType], width=30, state="readonly")
        fields["erp_type"].grid(row=1, column=1, padx=8, pady=4, sticky="w")
        fields["erp_type"].set(ERPType.ABACUS.value)

        tk.Label(win, text="API-URL:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        fields["api_url"] = tk.Entry(win, width=50)
        fields["api_url"].grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        fields["api_url"].insert(0, "https://")

        tk.Label(win, text="API-Key:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        fields["api_key"] = tk.Entry(win, width=50, show="*")
        fields["api_key"].grid(row=3, column=1, padx=8, pady=4, sticky="ew")

        tk.Label(win, text="Company ID:").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        fields["company_id"] = tk.Entry(win, width=50)
        fields["company_id"].grid(row=4, column=1, padx=8, pady=4, sticky="ew")

        tk.Label(win, text="Sync-Richtung:").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        fields["sync_direction"] = ttk.Combobox(win, values=[d.value for d in SyncDirection], width=30, state="readonly")
        fields["sync_direction"].grid(row=5, column=1, padx=8, pady=4, sticky="w")
        fields["sync_direction"].set(SyncDirection.BIDIRECTIONAL.value)

        tk.Label(win, text="Sync-Intervall (Min):").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        fields["interval"] = tk.Entry(win, width=10)
        fields["interval"].grid(row=6, column=1, padx=8, pady=4, sticky="w")
        fields["interval"].insert(0, "30")

        tk.Label(win, text="Aktiv:").grid(row=7, column=0, sticky="w", padx=8, pady=4)
        fields["enabled"] = tk.BooleanVar(value=True)
        tk.Checkbutton(win, variable=fields["enabled"]).grid(row=7, column=1, sticky="w")

        tk.Label(win, text="Auto-Sync:").grid(row=8, column=0, sticky="w", padx=8, pady=4)
        fields["auto_sync"] = tk.BooleanVar(value=False)
        tk.Checkbutton(win, variable=fields["auto_sync"]).grid(row=8, column=1, sticky="w")

        win.columnconfigure(1, weight=1)

        def save():
            name = fields["name"].get().strip()
            if not name:
                messagebox.showerror("Fehler", "Name ist erforderlich.")
                return

            config = ERPConfig(
                name=name,
                erp_type=fields["erp_type"].get(),
                api_url=fields["api_url"].get().strip(),
                api_key=fields["api_key"].get().strip(),
                company_id=fields["company_id"].get().strip(),
                sync_direction=fields["sync_direction"].get(),
                sync_interval_minutes=int(fields["interval"].get() or 30),
                enabled=fields["enabled"].get(),
                auto_sync=fields["auto_sync"].get(),
            )
            self.add_config(name, config)
            messagebox.showinfo("Hinzugefügt", f"ERP '{name}' hinzugefügt.")
            self._refresh_erp_gui()
            win.destroy()

        tk.Button(win, text="Hinzufügen", command=save, bg="darkgreen", fg="white").grid(row=9, column=0, columnspan=2, pady=16)

    def _edit_erp_gui_selected(self, tree):
        selection = tree.selection()
        if selection:
            name = tree.item(selection[0])["tags"][0]
            self._edit_erp_gui(name)

    def _edit_erp_gui(self, name: str):
        import tkinter as tk
        from tkinter import ttk, messagebox

        config = self.configs.get(name)
        if not config:
            return

        win = tk.Toplevel()
        win.title(f"ERP bearbeiten: {name}")
        win.geometry("700x600")

        fields = {}

        tk.Label(win, text="Name:").grid(row=0, column=0, sticky="w", padx=8, pady=4)
        fields["name"] = tk.Entry(win, width=50)
        fields["name"].grid(row=0, column=1, padx=8, pady=4, sticky="ew")
        fields["name"].insert(0, name)
        fields["name"].config(state="readonly")

        tk.Label(win, text="ERP-Typ:").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        fields["erp_type"] = ttk.Combobox(win, values=[t.value for t in ERPType], width=30, state="readonly")
        fields["erp_type"].grid(row=1, column=1, padx=8, pady=4, sticky="w")
        fields["erp_type"].set(config.erp_type)

        tk.Label(win, text="API-URL:").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        fields["api_url"] = tk.Entry(win, width=50)
        fields["api_url"].grid(row=2, column=1, padx=8, pady=4, sticky="ew")
        fields["api_url"].insert(0, config.api_url)

        tk.Label(win, text="API-Key:").grid(row=3, column=0, sticky="w", padx=8, pady=4)
        fields["api_key"] = tk.Entry(win, width=50, show="*")
        fields["api_key"].grid(row=3, column=1, padx=8, pady=4, sticky="ew")
        fields["api_key"].insert(0, config.api_key)

        tk.Label(win, text="Company ID:").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        fields["company_id"] = tk.Entry(win, width=50)
        fields["company_id"].grid(row=4, column=1, padx=8, pady=4, sticky="ew")
        fields["company_id"].insert(0, config.company_id)

        tk.Label(win, text="Sync-Richtung:").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        fields["sync_direction"] = ttk.Combobox(win, values=[d.value for d in SyncDirection], width=30, state="readonly")
        fields["sync_direction"].grid(row=5, column=1, padx=8, pady=4, sticky="w")
        fields["sync_direction"].set(config.sync_direction)

        tk.Label(win, text="Sync-Intervall (Min):").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        fields["interval"] = tk.Entry(win, width=10)
        fields["interval"].grid(row=6, column=1, padx=8, pady=4, sticky="w")
        fields["interval"].insert(0, str(config.sync_interval_minutes))

        tk.Label(win, text="Aktiv:").grid(row=7, column=0, sticky="w", padx=8, pady=4)
        fields["enabled"] = tk.BooleanVar(value=config.enabled)
        tk.Checkbutton(win, variable=fields["enabled"]).grid(row=7, column=1, sticky="w")

        tk.Label(win, text="Auto-Sync:").grid(row=8, column=0, sticky="w", padx=8, pady=4)
        fields["auto_sync"] = tk.BooleanVar(value=config.auto_sync)
        tk.Checkbutton(win, variable=fields["auto_sync"]).grid(row=8, column=1, sticky="w")

        win.columnconfigure(1, weight=1)

        def save():
            config.erp_type = fields["erp_type"].get()
            config.api_url = fields["api_url"].get().strip()
            config.api_key = fields["api_key"].get().strip()
            config.company_id = fields["company_id"].get().strip()
            config.sync_direction = fields["sync_direction"].get()
            config.sync_interval_minutes = int(fields["interval"].get() or 30)
            config.enabled = fields["enabled"].get()
            config.auto_sync = fields["auto_sync"].get()
            self._create_plugin(name, config)
            self._save_configs()
            self._refresh_erp_gui()
            messagebox.showinfo("Gespeichert", "ERP-Konfiguration gespeichert.")
            win.destroy()

        tk.Button(win, text="Speichern", command=save, bg="darkblue", fg="white").grid(row=9, column=0, columnspan=2, pady=16)

    def _delete_erp_gui_selected(self, tree):
        import tkinter.messagebox as messagebox
        selection = tree.selection()
        if selection:
            name = tree.item(selection[0])["tags"][0]
            if messagebox.askyesno("Löschen", f"ERP '{name}' wirklich löschen?"):
                self.remove_config(name)
                self._refresh_erp_gui()
                messagebox.showinfo("Gelöscht", "ERP entfernt.")

    def _test_erp_gui_selected(self, tree):
        selection = tree.selection()
        if selection:
            name = tree.item(selection[0])["tags"][0]
            self._test_single_erp(name)

    def _test_single_erp(self, name: str):
        import tkinter.messagebox as messagebox
        plugin = self.get_plugin(name)
        if not plugin:
            messagebox.showerror("Test", f"ERP '{name}' nicht gefunden.")
            return
        result = plugin.test_connection()
        if result.get("success"):
            messagebox.showinfo("Test", f"ERP '{name}' Verbindung erfolgreich!\n\nInfo: {result.get('info', 'OK')}")
        else:
            messagebox.showerror("Test", f"ERP '{name}' Verbindung fehlgeschlagen:\n{result.get('error', 'Unbekannt')}")

    def _test_all_gui(self):
        import tkinter.messagebox as messagebox
        results = self.test_all()
        if not results:
            messagebox.showinfo("Test", "Keine ERP-Systeme konfiguriert.")
            return
        msg = "ERP-Verbindungstests:\n\n"
        for name, result in results.items():
            status = "✓ Verbunden" if result.get("success") else f"✗ {result.get('error', 'Fehler')}"
            msg += f"  {name}: {status}\n"
        messagebox.showinfo("ERP-Tests", msg)

    def _import_projects_gui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox

        win = tk.Toplevel()
        win.title("Projekte importieren")
        win.geometry("900x600")

        cols = ("erp", "project_number", "project_name", "customer", "status", "budget")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        tree.heading("erp", text="ERP")
        tree.heading("project_number", text="Projektnr.")
        tree.heading("project_name", text="Projektname")
        tree.heading("customer", text="Kunde")
        tree.heading("status", text="Status")
        tree.heading("budget", text="Budget")
        tree.column("erp", width=80)
        tree.column("project_number", width=120)
        tree.column("project_name", width=250)
        tree.column("customer", width=180)
        tree.column("status", width=80)
        tree.column("budget", width=100, anchor="e")
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        all_projects = self.import_all_projects()
        total = 0
        for erp_name, projects in all_projects.items():
            for p in projects:
                tree.insert("", "end", values=(
                    erp_name,
                    p.project_number,
                    p.project_name,
                    p.customer_name,
                    p.status,
                    f"{p.budget:,.2f} {p.currency}"
                ))
                total += 1

        tk.Button(win, text=f"{total} Projekte importiert - Schliessen", command=win.destroy,
                  bg="darkgreen", fg="white").pack(pady=8)

    def _import_customers_gui(self):
        import tkinter as tk
        from tkinter import ttk, messagebox

        win = tk.Toplevel()
        win.title("Kunden importieren")
        win.geometry("900x600")

        cols = ("erp", "customer_number", "name", "email", "phone", "city")
        tree = ttk.Treeview(win, columns=cols, show="headings", height=20)
        tree.heading("erp", text="ERP")
        tree.heading("customer_number", text="Kundennr.")
        tree.heading("name", text="Name")
        tree.heading("email", text="E-Mail")
        tree.heading("phone", text="Telefon")
        tree.heading("city", text="Ort")
        tree.column("erp", width=80)
        tree.column("customer_number", width=120)
        tree.column("name", width=200)
        tree.column("email", width=200)
        tree.column("phone", width=120)
        tree.column("city", width=120)
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        all_customers = self.import_all_customers()
        total = 0
        for erp_name, customers in all_customers.items():
            for c in customers:
                tree.insert("", "end", values=(
                    erp_name,
                    c.customer_number,
                    c.name,
                    c.email,
                    c.phone,
                    c.city
                ))
                total += 1

        tk.Button(win, text=f"{total} Kunden importiert - Schliessen", command=win.destroy,
                  bg="darkgreen", fg="white").pack(pady=8)


# Demo / Test
if __name__ == "__main__":
    manager = ERPManager("test_erp_configs")

    # Demo-Plugin (Abacus, offline)
    abacus_config = ERPConfig(
        name="Abacus Test",
        erp_type=ERPType.ABACUS.value,
        api_url="",  # Offline-Modus
        sync_direction=SyncDirection.BIDIRECTIONAL.value,
        enabled=True,
    )
    manager.add_config("Abacus Test", abacus_config)

    # Test
    print("ERP-Manager initialisiert")
    print(f"Plugins: {list(manager.plugins.keys())}")
    print(f"Konfigurationen: {list(manager.configs.keys())}")

    # Verbindungstest (offline)
    for name, plugin in manager.plugins.items():
        result = plugin.test_connection()
        print(f"  {name}: {result}")

    # Projekte importieren (offline → Cache)
    projects = manager.import_all_projects()
    print(f"Importierte Projekte: {sum(len(p) for p in projects.values())}")

    # Kunden importieren (offline → Cache)
    customers = manager.import_all_customers()
    print(f"Importierte Kunden: {sum(len(c) for c in customers.values())}")

    print("\nERP-Ökosystem OK!")
