"""SIA 451 / CRB (Sorba) Adapter - fixed-width Format."""
from . import BaseImporter, register
from ..models import Devis, Position
from ..parsers import crb  # bestehender Parser


@register
class Sia451Importer(BaseImporter):
    name = "SIA 451 (Sorba/CRB)"
    extensions = ("sia", "crb")

    def parse(self, path: str) -> Devis:
        return crb.parse(path)
