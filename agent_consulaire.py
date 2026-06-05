#!/usr/bin/env python3
"""
Agent Consulaire IA — Traitement de dossier visa étudiant France (VLS-TS)
Propulsé par Groq (LLaMA-3.3) + extraction PDF + OCR — 100% gratuit
"""

import os
import sys
import pathlib
import pdfplumber
from groq import Groq

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.rule import Rule
from rich import box
from rich.align import Align

console = Console()

# ── Couleurs drapeau français ──────────────────────────────────────────────────
BLEU  = "#0055A4"
ROUGE = "#EF4135"

# ── Limites tokens pour tier gratuit Groq (12 000 TPM) ───────────────────────
MAX_CHARS_PAR_DOC = 400
MAX_TOTAL_CHARS   = 3_500

# ── Détection OCR (optionnel) ──────────────────────────────────────────────────
OCR_DISPONIBLE = False
try:
    import fitz          # PyMuPDF
    import pytesseract
    from PIL import Image
    import io

    # Chemin Tesseract Windows (installer depuis https://github.com/UB-Mannheim/tesseract/wiki)
    _TESSERACT_PATHS = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]
    for _p in _TESSERACT_PATHS:
        if pathlib.Path(_p).exists():
            pytesseract.pytesseract.tesseract_cmd = _p
            break

    OCR_DISPONIBLE = True
except ImportError:
    pass


# ─────────────────────────────────────────────────────────────────
#  SYSTEM PROMPT — Procédures consulaires 2024-2025 complètes
# ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Tu es un officier consulaire IA — visa étudiant long séjour France (VLS-TS), Ambassade de France en Guinée. Liste officielle consulat mai 2026.

DOCUMENTS REQUIS (7 catégories) :
1. Formulaire France-Visas (rempli en ligne)
2. Identité : photo fond blanc + passeport validité >15 mois + extrait de naissance
3. Séjour : attestation d'admission université France (accord préalable)
4. Finances (1 seule option) : A) compte bloqué 7380€ Guinée + attestation virement irrévocable | B) garant France : engagement honneur + CNI + attestation travail + bulletins salaire 3 mois + avis imposition + relevés bancaires 3 mois | C) attestation bourse
5. Hébergement (1 seule option) : A) attestation hébergement : déclaration honneur + CNI hébergeant + bail/titre propriété + facture eau-électricité + quittance | B) contrat de bail | C) attestation logement organisme
6. Assurance voyage (1er mois après arrivée France)
7. Réservation billets d'avion

ANALYSE EN 5 ÉTAPES :
1. INVENTAIRE des documents reçus
2. ANALYSE : ✅ CONFORME / ⚠️ INSUFFISANT / ❌ MANQUANT
3. ÉVALUATION note /10, points forts, points faibles
4. DÉCISION : ✅ VISA ACCORDÉ ou ❌ VISA REFUSÉ + motif
5. RECOMMANDATIONS correctives

Ton officiel et neutre. N'invente aucune exigence hors liste. Simulation pédagogique — voir france-visas.gouv.fr pour procédure officielle."""


# ─────────────────────────────────────────────────────────────────
#  DESIGN — Bannière tricolore
# ─────────────────────────────────────────────────────────────────
def print_banner():
    console.print()
    ligne = Text()
    ligne.append("█" * 26, style=f"bold {BLEU}")
    ligne.append("█" * 26, style="bold white on white")
    ligne.append("█" * 26, style=f"bold {ROUGE}")
    console.print(ligne)

    titre = Text(justify="center")
    titre.append("\n")
    titre.append("  🇫🇷  AMBASSADE DE FRANCE — SERVICE DES VISAS  🇫🇷  \n", style="bold white")
    titre.append("      Agent IA · Traitement dossier visa étudiant (VLS-TS)      \n", style="dim white")
    titre.append("\n")

    console.print(Panel(
        Align.center(titre),
        style="white on #0a0a1a",
        border_style=BLEU,
        padding=(0, 2),
    ))
    console.print(ligne)
    console.print()


# ─────────────────────────────────────────────────────────────────
#  EXTRACTION DE TEXTE
# ─────────────────────────────────────────────────────────────────
def ocr_image(image_bytes: bytes) -> str:
    """OCR sur un objet bytes représentant une image."""
    if not OCR_DISPONIBLE:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        return pytesseract.image_to_string(img, lang="fra+eng").strip()
    except Exception:
        return ""


def extract_text_from_pdf(pdf_path: pathlib.Path) -> str:
    """
    1. Essaie pdfplumber (PDF texte natif)
    2. Si vide → tente OCR page par page avec PyMuPDF + Tesseract
    """
    # Tentative 1 : texte natif
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages).strip()
        if text:
            return text
    except Exception:
        pass

    # Tentative 2 : OCR si PDF scanné
    if not OCR_DISPONIBLE:
        return "(PDF scanné — OCR non disponible. Voir instructions d'installation.)"

    try:
        doc = fitz.open(str(pdf_path))
        pages_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            page_text = ocr_image(img_bytes)
            if page_text:
                pages_text.append(page_text)
        doc.close()
        result = "\n\n".join(pages_text).strip()
        return result if result else "(PDF scanné — aucun texte détecté par OCR)"
    except Exception as e:
        return f"(Erreur OCR : {e})"


def extract_text_from_image(img_path: pathlib.Path) -> str:
    """OCR direct sur un fichier image (JPG, PNG…)."""
    if not OCR_DISPONIBLE:
        return "(Image — OCR non disponible. Voir instructions d'installation.)"
    try:
        with open(str(img_path), "rb") as f:
            return ocr_image(f.read())
    except Exception as e:
        return f"(Erreur OCR image : {e})"


# ─────────────────────────────────────────────────────────────────
#  CHARGEMENT DU DOSSIER
# ─────────────────────────────────────────────────────────────────
TYPES_SUPPORTES = {
    ".pdf":  "pdf",
    ".jpg":  "image",
    ".jpeg": "image",
    ".png":  "image",
    ".webp": "image",
}


def load_documents(folder_path: str) -> list[tuple[str, str]]:
    folder = pathlib.Path(folder_path)
    if not folder.exists():
        raise FileNotFoundError(f"Le dossier '{folder_path}' est introuvable.")

    fichiers = sorted([
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in TYPES_SUPPORTES
    ])

    if not fichiers:
        raise ValueError(
            f"Aucun fichier PDF ou image trouvé dans :\n{folder.resolve()}\n"
            f"Formats acceptés : {', '.join(TYPES_SUPPORTES.keys())}"
        )

    # Info OCR
    statut_ocr = f"[green]✅ Disponible[/]" if OCR_DISPONIBLE else f"[{ROUGE}]⚠️  Non installé[/]"
    console.print(f"  OCR (documents scannés / images) : {statut_ocr}\n")

    table = Table(
        title=f"[bold {BLEU}]Documents détectés ({len(fichiers)} fichier(s))[/]",
        box=box.ROUNDED,
        border_style=BLEU,
        header_style=f"bold {BLEU}",
        show_lines=True,
    )
    table.add_column("N°", width=4, justify="center", style="dim")
    table.add_column("Fichier", style="bold white")
    table.add_column("Type", width=7, justify="center")
    table.add_column("Taille", justify="right", style="dim")
    table.add_column("Statut", justify="center", width=14)

    documents = []

    with Progress(
        SpinnerColumn(style=BLEU),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=28, style="on #1a1a2e", complete_style=BLEU),
        TextColumn("[bold white]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"[{BLEU}]Extraction...", total=len(fichiers))

        for i, fichier in enumerate(fichiers, 1):
            progress.update(task, description=f"[{BLEU}]Lecture : [white]{fichier.name}")
            size_kb = fichier.stat().st_size / 1024
            type_doc = TYPES_SUPPORTES[fichier.suffix.lower()]

            if type_doc == "pdf":
                text = extract_text_from_pdf(fichier)
                badge_type = "[cyan]PDF[/]"
            else:
                text = extract_text_from_image(fichier)
                badge_type = "[magenta]IMG[/]"

            if text and "non disponible" not in text and "Erreur" not in text:
                if len(text) > MAX_CHARS_PAR_DOC:
                    text = text[:MAX_CHARS_PAR_DOC] + "\n[... tronqué ...]"
                statut = "[green]✅ Extrait[/]"
            elif "non disponible" in text:
                statut = f"[{ROUGE}]📷 OCR requis[/]"
            else:
                statut = f"[{ROUGE}]⚠️  Vide[/]"
                text = text or "(document vide)"

            documents.append((fichier.name, text))
            table.add_row(str(i), fichier.name, badge_type, f"{size_kb:.0f} Ko", statut)
            progress.advance(task)

    console.print(table)
    console.print()

    # Plafond global
    total_chars = sum(len(t) for _, t in documents)
    if total_chars > MAX_TOTAL_CHARS:
        facteur = MAX_TOTAL_CHARS / total_chars
        documents = [(n, t[:max(300, int(len(t) * facteur))]) for n, t in documents]
        console.print(f"[dim {BLEU}]ℹ  Textes ajustés pour respecter la limite API gratuite.[/]\n")

    return documents


# ─────────────────────────────────────────────────────────────────
#  PROMPT D'ANALYSE
# ─────────────────────────────────────────────────────────────────
def build_analysis_prompt(documents: list[tuple[str, str]]) -> str:
    section = ""
    for i, (name, text) in enumerate(documents, 1):
        section += f"\n{'─'*60}\nDOCUMENT {i} — {name}\n{'─'*60}\n{text}\n"

    return (
        f"Voici le dossier complet de demande de visa étudiant long séjour VLS-TS pour la France.\n"
        f"Nombre de documents soumis : {len(documents)}\n"
        f"{section}\n\n"
        "Procédez à l'analyse consulaire officielle complète selon les 5 étapes de la procédure "
        "interne 2026 (liste officielle consulat). Soyez précise et rigoureuse comme lors d'un vrai traitement de dossier."
    )


# ─────────────────────────────────────────────────────────────────
#  AFFICHAGE
# ─────────────────────────────────────────────────────────────────
def print_rapport(texte: str):
    upper = texte.upper()
    if "VISA ACCORDÉ" in upper or "ACCORD" in upper:
        border, icone = "green", "✅"
    elif "VISA REFUSÉ" in upper or "REFUS" in upper:
        border, icone = ROUGE, "❌"
    else:
        border, icone = BLEU, "📋"

    console.print(Panel(
        texte,
        title=f"[bold {BLEU}]{icone}  Rapport Consulaire — Mme Sophie Martin[/]",
        border_style=border,
        padding=(1, 2),
    ))


def print_reponse(texte: str):
    console.print(Panel(
        texte,
        title=f"[bold {BLEU}]Mme Sophie Martin[/]",
        border_style=BLEU,
        padding=(1, 2),
    ))
    console.print()


# ─────────────────────────────────────────────────────────────────
#  BOUCLE PRINCIPALE
# ─────────────────────────────────────────────────────────────────
def main():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        console.print(Panel(
            f"[bold {ROUGE}]Variable GROQ_API_KEY non définie.[/]\n\n"
            "Dans PowerShell :\n"
            f'[bold {BLEU}]$env:GROQ_API_KEY = "gsk_..."[/]',
            title="❌ Clé API manquante",
            border_style=ROUGE,
        ))
        sys.exit(1)

    client = Groq(api_key=api_key)
    print_banner()

    console.print(f"[{BLEU}]Indiquez le chemin complet du dossier contenant vos documents.[/]")
    console.print(f'[dim]Exemple : C:\\Users\\Mohamed\\Documents\\mon_dossier_visa[/]\n')

    while True:
        folder = console.input(f"[bold {BLEU}]📁 Chemin du dossier : [/]").strip().strip('"').strip("'")
        if folder:
            break

    console.print()
    try:
        documents = load_documents(folder)
    except (FileNotFoundError, ValueError) as e:
        console.print(Panel(str(e), title="❌ Erreur", border_style=ROUGE))
        sys.exit(1)

    console.print(Rule(f"[bold {BLEU}]  ANALYSE CONSULAIRE EN COURS  [/]", style=BLEU))
    console.print()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({"role": "user", "content": build_analysis_prompt(documents)})

    with console.status(f"[{BLEU}]Mme Martin examine votre dossier...[/]", spinner="dots", spinner_style=BLEU):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=4096,
            )
            reply = response.choices[0].message.content
            messages.append({"role": "assistant", "content": reply})
        except Exception as e:
            console.print(Panel(f"[red]Erreur API Groq : {e}[/]", title="❌ Erreur", border_style=ROUGE))
            sys.exit(1)

    print_rapport(reply)

    console.print(Rule(style=BLEU))
    console.print(f"\n[dim]Posez vos questions complémentaires. Tapez [bold]quitter[/] pour terminer.[/]\n")

    while True:
        try:
            user_input = console.input("[bold white]Vous : [/]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not user_input:
            continue

        if user_input.lower() in ("quitter", "exit", "quit", "q"):
            console.print(Panel(
                "Votre dossier a été enregistré dans notre système.\n"
                "Vous recevrez la décision officielle par courrier dans les délais habituels.\n\n"
                "[dim]Simulation pédagogique — Procédure officielle : france-visas.gouv.fr[/]",
                title=f"[bold {BLEU}]Mme Sophie Martin — Fin de session[/]",
                border_style=BLEU,
                padding=(1, 2),
            ))
            break

        messages.append({"role": "user", "content": user_input})

        with console.status(f"[{BLEU}]Mme Martin rédige sa réponse...[/]", spinner="dots", spinner_style=BLEU):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=messages,
                    max_tokens=2048,
                )
                reply = response.choices[0].message.content
                messages.append({"role": "assistant", "content": reply})
            except Exception as e:
                console.print(f"[{ROUGE}]⚠️  Erreur : {e}[/]\n")
                continue

        print_reponse(reply)


if __name__ == "__main__":
    main()
