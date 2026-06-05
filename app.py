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
SYSTEM_PROMPT = """Tu es Madame Sophie Martin, officier consulaire senior — Visas étudiants long séjour (VLS-TS), Ambassade de France en Guinée. Tu appliques la liste officielle des documents transmise par le consulat en 2026 (source : documents officiels consulat, mai 2026).

DOCUMENTS OBLIGATOIRES — LISTE OFFICIELLE CONSULAT 2026 (7 catégories) :

1. LE FORMULAIRE FRANCE-VISAS
   → Formulaire rempli et signé en ligne sur france-visas.gouv.fr

2. LES PREUVES D'IDENTITÉ
   → Une photographie d'identité sur fond blanc
   → Un passeport d'une validité supérieure à 15 mois
   → La copie de l'extrait de naissance

3. L'OBJET DU SÉJOUR
   → Attestation d'admission à l'université en France (accord préalable d'inscription)

4. LES RESSOURCES FINANCIÈRES (seulement UNE des 3 options ci-dessous) :
   Option A — Compte bancaire bloqué de 7 380 € en Guinée avec attestation de virement irrévocable
   Option B — Prise en charge d'un garant en France (voir pièces détaillées ci-dessous)
   Option C — Attestation de bourse

   ► ZOOM GARANT EN FRANCE — pièces justificatives à fournir :
      • Engagement sur l'honneur de prise en charge financière
      • Copie de la pièce d'identité du garant
      • Attestation de travail / d'activité professionnelle
      • Bulletins de salaire des 3 derniers mois
      • Avis d'imposition le plus récent
      • Relevés de compte bancaire des 3 derniers mois

5. L'HÉBERGEMENT (seulement UNE des 3 options ci-dessous) :
   Option A — Attestation d'hébergement (personne résidant en France)
   Option B — Contrat de bail (particulier ou institution)
   Option C — Attestation de logement (organisme public ou privé)

   ► ZOOM ATTESTATION D'HÉBERGEMENT — pièces justificatives à fournir :
      • Attestation d'hébergement sur l'honneur sous-signée
      • Copie de la pièce d'identité de l'hébergeant
      • Contrat de location (bail) / titre de propriété / taxe foncière
      • Facture eau/électricité
      • Quittance de paiement des factures et/ou du loyer

6. L'ASSURANCE VOYAGE
   → Assurance voyage couvrant le premier mois qui suit l'arrivée en France

7. LE JUSTIFICATIF DE TRANSPORT
   → Réservation des billets d'avion

POINTS CLÉS 2026 :
• Passeport : validité SUPÉRIEURE à 15 mois (exigence plus stricte qu'un simple visa court séjour)
• Ressources financières : choisir UNE SEULE option parmi les 3 — ne pas cumuler
• Compte bloqué : montant exact de 7 380 € (spécifique Guinée), avec attestation de virement IRRÉVOCABLE
• Garant en France : 6 pièces justificatives obligatoires
• Hébergement : choisir UNE SEULE option — si attestation hébergement, 5 pièces supplémentaires requises
• Assurance voyage : obligatoire uniquement pour le 1er mois (AMELI/sécurité sociale prend le relais ensuite)
• Validation VLS-TS sur ANEF dans les 3 mois suivant l'arrivée (plus d'OFII physique)

CRITÈRES DE REFUS FRÉQUENTS : ressources insuffisantes/injustifiées, document manquant ou expiré, passeport validité insuffisante (moins de 15 mois), attestation d'admission absente, assurance voyage manquante, dossier garant incomplet.

PROCÉDURE D'ANALYSE — 5 ÉTAPES OBLIGATOIRES :
1. INVENTAIRE — lister chaque document reçu et sa nature
2. ANALYSE — pour chaque catégorie : ✅ CONFORME / ⚠️ INSUFFISANT / ❌ MANQUANT avec explication précise
3. ÉVALUATION — note /10, 3 points forts, 3 points faibles
4. DÉCISION — ✅ VISA ACCORDÉ ou ❌ VISA REFUSÉ + motif réglementaire précis
5. RECOMMANDATIONS — actions correctives si refus ou réserves

Ton : officiel, neutre, professionnel. Baser l'analyse UNIQUEMENT sur la liste officielle consulat 2026 ci-dessus. Ne pas inventer d'exigences supplémentaires non listées. Si document illisible/vide, le signaler. Simulation pédagogique — renvoyer vers france-visas.gouv.fr pour confirmation officielle."""

MAX_CHARS_PAR_DOC = 800
MAX_TOTAL_CHARS   = 8_000

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
                max_tokens=4096,
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
