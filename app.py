#!/usr/bin/env python3
"""
Agent Consulaire IA — Interface Web Streamlit
Visa étudiant long séjour — Liste officielle consulat 2026
"""

import io
import pathlib
import tempfile

import pdfplumber
import streamlit as st
from groq import Groq

# ── Tentative OCR (optionnel, disponible sur Streamlit Cloud avec packages.txt) ──
OCR_DISPONIBLE = False
try:
    import fitz
    import pytesseract
    from PIL import Image
    OCR_DISPONIBLE = True
except ImportError:
    pass

# ─────────────────────────────────────────────────────────────────
#  SYSTEM PROMPT — Liste officielle consulat 2026
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

MAX_CHARS_PAR_DOC = 400
MAX_TOTAL_CHARS   = 3_500

# ─────────────────────────────────────────────────────────────────
#  EXTRACTION DE TEXTE
# ─────────────────────────────────────────────────────────────────
def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            pages = [p.extract_text() or "" for p in pdf.pages]
        text = "\n\n".join(pages).strip()
        if text:
            return text
    except Exception:
        pass

    if not OCR_DISPONIBLE:
        return "(PDF scanné — OCR non disponible sur ce déploiement)"

    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        pages_text = []
        for page in doc:
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            t = pytesseract.image_to_string(img, lang="fra+eng").strip()
            if t:
                pages_text.append(t)
        doc.close()
        result = "\n\n".join(pages_text).strip()
        return result if result else "(PDF scanné — aucun texte détecté)"
    except Exception as e:
        return f"(Erreur OCR : {e})"


def extract_text_from_image(file_bytes: bytes) -> str:
    if not OCR_DISPONIBLE:
        return "(Image — OCR non disponible sur ce déploiement)"
    try:
        img = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(img, lang="fra+eng").strip()
    except Exception as e:
        return f"(Erreur OCR image : {e})"


def extract_text(uploaded_file) -> str:
    ext = pathlib.Path(uploaded_file.name).suffix.lower()
    data = uploaded_file.read()
    if ext == ".pdf":
        return extract_text_from_pdf(data)
    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        return extract_text_from_image(data)
    return "(Format non supporté)"


def build_analysis_prompt(documents: list[tuple[str, str]]) -> str:
    section = ""
    for i, (name, text) in enumerate(documents, 1):
        section += f"\n{'─'*60}\nDOCUMENT {i} — {name}\n{'─'*60}\n{text}\n"
    return (
        f"Voici le dossier complet de demande de visa étudiant long séjour VLS-TS pour la France.\n"
        f"Nombre de documents soumis : {len(documents)}\n"
        f"{section}\n\n"
        "Procédez à l'analyse consulaire officielle complète selon les 5 étapes de la procédure "
        "interne 2026 (liste officielle consulat). Soyez précise et rigoureuse."
    )


# ─────────────────────────────────────────────────────────────────
#  PAGE STREAMLIT
# ─────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Agent Visa France 🇫🇷",
    page_icon="🇫🇷",
    layout="centered",
)

st.title("🇫🇷 Agent Consulaire IA — Visa Étudiant France")
st.caption("Analyse de dossier · Liste officielle consulat 2026 · Simulation pédagogique")

# ── Clé API ──────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuration")

    # Priorité : secrets Streamlit Cloud > saisie manuelle
    api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
    if not api_key:
        api_key = st.text_input(
            "Clé API Groq",
            type="password",
            placeholder="gsk_...",
            help="Créez un compte gratuit sur console.groq.com pour obtenir votre clé.",
        )

    st.divider()
    st.markdown("**Documents acceptés :** PDF, JPG, PNG, WEBP")
    st.markdown("**Liste basée sur :** Documents officiels consulat de France en Guinée — Mai 2026")
    st.markdown("---")
    st.caption("Simulation pédagogique. Pour la procédure officielle : [france-visas.gouv.fr](https://france-visas.gouv.fr)")

# ── Upload ────────────────────────────────────────────────────────
st.subheader("📁 Déposez vos documents")
uploaded_files = st.file_uploader(
    "Sélectionnez tous vos fichiers (PDF et/ou images)",
    type=["pdf", "jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
)

if uploaded_files:
    st.success(f"✅ {len(uploaded_files)} fichier(s) chargé(s)")
    with st.expander("Voir les fichiers chargés"):
        for f in uploaded_files:
            st.write(f"• {f.name}")

# ── Analyse ───────────────────────────────────────────────────────
if st.button("🔍 Analyser mon dossier", type="primary", disabled=not (uploaded_files and api_key)):
    if not api_key:
        st.error("Veuillez entrer votre clé API Groq dans la barre latérale.")
        st.stop()

    # Extraction du texte
    documents = []
    with st.spinner("Lecture des documents..."):
        for f in uploaded_files:
            text = extract_text(f)
            if len(text) > MAX_CHARS_PAR_DOC:
                text = text[:MAX_CHARS_PAR_DOC] + "\n[... tronqué ...]"
            documents.append((f.name, text))

        # Plafond global tokens
        total = sum(len(t) for _, t in documents)
        if total > MAX_TOTAL_CHARS:
            facteur = MAX_TOTAL_CHARS / total
            documents = [(n, t[:max(300, int(len(t) * facteur))]) for n, t in documents]

    # Appel Groq
    client = Groq(api_key=api_key)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": build_analysis_prompt(documents)},
    ]

    with st.spinner("Mme Martin examine votre dossier..."):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                max_tokens=1500,
            )
            rapport = response.choices[0].message.content
            messages.append({"role": "assistant", "content": rapport})
            st.session_state["messages"] = messages
        except Exception as e:
            st.error(f"Erreur API Groq : {e}")
            st.stop()

    # Affichage rapport
    upper = rapport.upper()
    if "VISA ACCORDÉ" in upper or "ACCORD" in upper:
        st.success("### ✅ Rapport Consulaire — Mme Sophie Martin")
    elif "VISA REFUSÉ" in upper or "REFUS" in upper:
        st.error("### ❌ Rapport Consulaire — Mme Sophie Martin")
    else:
        st.info("### 📋 Rapport Consulaire — Mme Sophie Martin")

    st.markdown(rapport)
    st.divider()

# ── Chat suivi ────────────────────────────────────────────────────
if "messages" in st.session_state:
    st.subheader("💬 Questions complémentaires")
    question = st.chat_input("Posez une question à Mme Martin...")

    if question:
        st.session_state["messages"].append({"role": "user", "content": question})

        client = Groq(api_key=api_key or st.secrets.get("GROQ_API_KEY", ""))
        with st.spinner("Mme Martin rédige sa réponse..."):
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=st.session_state["messages"],
                    max_tokens=2048,
                )
                reply = response.choices[0].message.content
                st.session_state["messages"].append({"role": "assistant", "content": reply})
            except Exception as e:
                st.error(f"Erreur : {e}")

    # Afficher l'historique du chat (uniquement les échanges après le rapport initial)
    chat_messages = st.session_state["messages"][2:]  # skip system + premier rapport
    for msg in chat_messages:
        with st.chat_message("user" if msg["role"] == "user" else "assistant"):
            st.markdown(msg["content"])
