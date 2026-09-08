import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas that computes total pages for footer 'Page X sur Y'."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        # Suppress headers and footers on cover page
        if self._pageNumber > 1:
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#718096"))
            # Header
            self.drawString(
                54, A4[1] - 36,
                "AntCode Hub 48h Sprint | Scénario B - Track 2 (Backend Engineering)"
            )
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, A4[1] - 42, A4[0] - 54, A4[1] - 42)

            # Footer
            self.line(54, 45, A4[0] - 54, 45)
            self.drawString(
                54, 32,
                "Dépôt GitHub: https://github.com/hakimi-yvon/antcode-ecommerce-backend"
            )
            page_text = f"Page {self._pageNumber} sur {page_count}"
            self.drawRightString(A4[0] - 54, 32, page_text)
        self.restoreState()


def build_pdf(filename="AntCode_Presentation_Projet_Hakimi_Yvon.pdf"):
    pdf_path = os.path.abspath(filename)
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    primary_color = colors.HexColor("#1A365D")
    secondary_color = colors.HexColor("#2B6CB0")
    text_color = colors.HexColor("#2D3748")
    accent_bg = colors.HexColor("#EDF2F7")

    title_style = ParagraphStyle(
        "CoverTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "CoverSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        alignment=1,
    )
    h1_style = ParagraphStyle(
        "Heading1_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        "Heading2_Custom",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_color,
        spaceAfter=5,
    )
    bullet_style = ParagraphStyle(
        "Bullet_Custom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=text_color,
        leftIndent=14,
        spaceAfter=3,
    )
    code_style = ParagraphStyle(
        "Code_Custom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1A202C"),
    )
    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=text_color,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#1A365D"),
    )

    story = []

    # ==========================================
    # PAGE 1: COUVERTURE & FICHE SIGNALÉTIQUE
    # ==========================================
    story.append(Spacer(1, 40))
    story.append(Paragraph("ANTCODE HUB ELITE ENGINEERING SPRINT", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Plateforme Logistique E-Commerce & Moteur de Paiement Mobile Money", title_style))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Dossier Technique & Architecture Système (Scénario B — Track 2: Backend)", subtitle_style))
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=2, color=secondary_color, spaceAfter=20))

    meta_info = [
        [Paragraph("<b>Candidat :</b>", table_cell_bold), Paragraph("Hakimi Yvon (yvonndouanla@gmail.com)", table_cell_style)],
        [Paragraph("<b>Compte GitHub :</b>", table_cell_bold), Paragraph("https://github.com/hakimi-yvon", table_cell_style)],
        [Paragraph("<b>Dépôt du projet :</b>", table_cell_bold), Paragraph("https://github.com/hakimi-yvon/antcode-ecommerce-backend", table_cell_style)],
        [Paragraph("<b>Épreuve :</b>", table_cell_bold), Paragraph("Scénario B (E-Commerce Logistics Crisis) | Track 2 (Backend / Fullstack)", table_cell_style)],
        [Paragraph("<b>Stack Technique :</b>", table_cell_bold), Paragraph("Python 3.14, Django 6.1, Django REST Framework, SQLite/PostgreSQL, Tabulate", table_cell_style)],
        [Paragraph("<b>Statut de validation :</b>", table_cell_bold), Paragraph("<b>100% Validé (6/6 tests unitaires OK, 500+ commandes seedées)</b>", table_cell_style)],
    ]
    meta_table = Table(meta_info, colWidths=[120, 365])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F7FAFC")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#E2E8F0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    story.append(meta_table)

    story.append(Spacer(1, 25))
    story.append(Paragraph("1. Résumé Exécutif & Vision du Projet", h1_style))
    story.append(Paragraph(
        "Au Cameroun, le commerce électronique fait face à une crise logistique majeure : commandes égarées, adresses urbaines sans numérotation ni code postal (Douala, Yaoundé), retries multiples des réseaux de paiement (MTN Mobile Money, Orange Money) provoquant des doublons, et saturation des bases de données lors des pics de fin de mois.",
        body_style
    ))
    story.append(Paragraph(
        "Ce projet livre une <b>solution backend complète, résiliente et hautement performante</b> conçue pour les contraintes réelles du marché camerounais :",
        body_style
    ))
    story.append(Paragraph("• <b>Adressage informel géolocalisé :</b> Prise en charge native des quartiers (Akwa, Bastos, Mendong...) et repères visuels réels.", bullet_style))
    story.append(Paragraph("• <b>Webhook Mobile Money idempotent :</b> Traitement sécurisé des callbacks MTN MoMo et Orange Money avec verrouillage atomique (`SELECT FOR UPDATE`) empêchant tout double-crédit.", bullet_style))
    story.append(Paragraph("• <b>Optimisation sous forte charge :</b> Indexation SQL composite éliminant les scans de tables ($O(N)$) et assurant des temps de réponse moyens sous 0,15 ms pour 1 000 requêtes.", bullet_style))
    story.append(Paragraph("• <b>Flux livreur économe en batterie et data :</b> Regroupement par quartier pour téléphones d'entrée de gamme en 3G instable.", bullet_style))

    story.append(PageBreak())

    # ==========================================
    # PAGE 2: STRUCTURE DU PROJET & MODÈLES
    # ==========================================
    story.append(Paragraph("2. Structure & Organisation du Codebase", h1_style))
    story.append(Paragraph(
        "Le projet suit une architecture modulaire propre et découplée, standard pour les applications Django en production :",
        body_style
    ))

    tree_data = [
        [Paragraph("<b>Chemin du Fichier / Dossier</b>", table_cell_bold), Paragraph("<b>Description & Rôle Architectural</b>", table_cell_bold)],
        [Paragraph("<code>config/settings.py</code>", code_style), Paragraph("Configuration globale, apps Django/DRF, secrets webhooks MoMo/OM.", table_cell_style)],
        [Paragraph("<code>config/urls.py</code>", code_style), Paragraph("Routage racine et inclusion de l'API v1 (<code>/api/v1/</code>).", table_cell_style)],
        [Paragraph("<code>logistics/models.py</code>", code_style), Paragraph("Schéma relationnel : Customer, Address, Product, Driver, Order, PaymentTransaction, Tracking.", table_cell_style)],
        [Paragraph("<code>logistics/views.py</code>", code_style), Paragraph("Contrôleurs : Webhook idempotent, CRUD Orders, Flux livreur quartier, Métriques goulots.", table_cell_style)],
        [Paragraph("<code>logistics/serializers.py</code>", code_style), Paragraph("Sérialisation DRF, validation des payloads webhook et conversion JSON.", table_cell_style)],
        [Paragraph("<code>logistics/admin.py</code>", code_style), Paragraph("Interface d'administration Django prête à l'emploi avec filtres avancés.", table_cell_style)],
        [Paragraph("<code>logistics/tests.py</code>", code_style), Paragraph("Suite de 6 tests automatisés (sécurité, idempotence, transitions de statut).", table_cell_style)],
        [Paragraph("<code>logistics/management/commands/seed_mock_data.py</code>", code_style), Paragraph("Générateur de 500+ commandes réalistes (Douala/Yaoundé) avec insertion atomique.", table_cell_style)],
        [Paragraph("<code>logistics/management/commands/import_legacy_data.py</code>", code_style), Paragraph("Pipeline ETL assainissant et important les 1 000 commandes historiques sales (CSV).", table_cell_style)],
        [Paragraph("<code>benchmark_queries.py</code>", code_style), Paragraph("Script de benchmarking SQL mesurant les plans d'exécution EXPLAIN sur 1 000 itérations.", table_cell_style)],
        [Paragraph("<code>README.md</code>", code_style), Paragraph("Documentation officielle, Prompt Ledger IA, rapport d'indexation, pitch vidéo.", table_cell_style)],
    ]
    tree_table = Table(tree_data, colWidths=[175, 310])
    tree_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(tree_table)

    story.append(Spacer(1, 15))
    story.append(Paragraph("3. Modèle de Données Relationnel Normalisé (MCD)", h1_style))
    story.append(Paragraph(
        "La base de données évite toute duplication grâce à une normalisation stricte (3FN) adaptée au contexte :",
        body_style
    ))

    models_info = [
        [Paragraph("<b>Entité</b>", table_cell_bold), Paragraph("<b>Attributs majeurs</b>", table_cell_bold), Paragraph("<b>Rôle & Spécificité locale</b>", table_cell_bold)],
        [Paragraph("<b>Customer</b>", table_cell_style), Paragraph("full_name, phone_number, email", table_cell_style), Paragraph("Téléphone indexé (+237 67x MTN / 69x Orange).", table_cell_style)],
        [Paragraph("<b>Address</b>", table_cell_style), Paragraph("city, neighborhood, landmark_reference, contact_phone", table_cell_style), Paragraph("Index composite (city, neighborhood). Pas de code postal : repères visuels obligatoires.", table_cell_style)],
        [Paragraph("<b>Product</b>", table_cell_style), Paragraph("sku (unique), name, category, unit_price_fcfa, stock", table_cell_style), Paragraph("Montant exact en FCFA (sans centimes).", table_cell_style)],
        [Paragraph("<b>DeliveryDriver</b>", table_cell_style), Paragraph("driver_id, vehicle_type (Moto/Van), is_available", table_cell_style), Paragraph("Gestion des motos-taxis (benskin) et camionnettes.", table_cell_style)],
        [Paragraph("<b>Order</b>", table_cell_style), Paragraph("order_id (unique), status, payment_status, total_fcfa, driver", table_cell_style), Paragraph("Index composites `(status, created_at)` et `(driver, status)` pour optimiser le dispatch.", table_cell_style)],
        [Paragraph("<b>PaymentTransaction</b>", table_cell_style), Paragraph("idempotency_key (unique), provider_tx_id, amount_fcfa, raw_payload", table_cell_style), Paragraph("Grand livre d'audit immuable garantissant la sécurité des transactions Mobile Money.", table_cell_style)],
    ]
    models_table = Table(models_info, colWidths=[95, 185, 205])
    models_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(models_table)

    story.append(PageBreak())

    # ==========================================
    # PAGE 3: LE WEBHOOK MOBILE MONEY & SÉCURITÉ
    # ==========================================
    story.append(Paragraph("4. Fonctionnement du Webhook Mobile Money Sécurisé", h1_style))
    story.append(Paragraph(
        "Le paiement par Mobile Money (MTN MoMo & Orange Money) représente plus de 85% des transactions e-commerce au Cameroun. Les pannes réseau intermittentes provoquent régulièrement des renvois automatiques de callbacks. Notre système intègre une architecture fintech triple-couche :",
        body_style
    ))

    story.append(Paragraph("A. Vérification de Signature & Token Secret", h2_style))
    story.append(Paragraph(
        "Chaque requête arrivant sur <code>/api/v1/payments/webhook/</code> doit obligatoirement fournir un en-tête <code>X-Callback-Secret</code> ou une signature cryptographique HMAC-SHA256 (<code>X-Signature</code>). Les requêtes non authentifiées sont immédiatement rejetées avec un code HTTP 401.",
        body_style
    ))

    story.append(Paragraph("B. Idempotence Stricte (Protection Anti-Doublons)", h2_style))
    story.append(Paragraph(
        "Une clé d'idempotence unique (<code>idempotency_key</code>) est enregistrée pour chaque événement. Si l'opérateur télécom réémet le même callback 2 ou 3 fois, l'API détecte l'existence préalable et renvoie immédiatement un HTTP 200 avec le statut <code>already_processed</code>, évitant toute double comptabilisation.",
        body_style
    ))

    story.append(Paragraph("C. Verrouillage Concurrentiel & Détection de Fraude", h2_style))
    story.append(Paragraph(
        "L'opération s'exécute dans un bloc atomique avec verrouillage de ligne : <code>Order.objects.select_for_update()</code>. De plus, une vérification stricte compare le montant reçu au total de la commande : si un attaquant envoie 500 FCFA pour une commande de 89 000 FCFA, la transaction est rejetée et archivée pour fraude.",
        body_style
    ))

    story.append(Spacer(1, 10))
    story.append(Paragraph("5. Rapport d'Optimisation des Requêtes & Indexation SQL", h1_style))
    story.append(Paragraph(
        "Lors des pics de commande (fin de mois, soldes), les requêtes non indexées génèrent des <i>Table Scans</i> ($O(N)$) qui saturent le processeur. Voici les résultats obtenus avec notre script de benchmark sur 1 000 itérations :",
        body_style
    ))

    bench_data = [
        [Paragraph("<b>Cas d'usage</b>", table_cell_bold), Paragraph("<b>Filtre SQL</b>", table_cell_bold), Paragraph("<b>Index actif</b>", table_cell_bold), Paragraph("<b>Temps (1 000 itér.)</b>", table_cell_bold), Paragraph("<b>Gain d'Architecture</b>", table_cell_bold)],
        [Paragraph("<b>Livreur en tournée</b>", table_cell_style), Paragraph("WHERE driver_id = ? AND status = ?", code_style), Paragraph("idx_order_driver_status", code_style), Paragraph("<b>117.34 ms</b>", table_cell_style), Paragraph("Recherche B-Tree directe O(log N).", table_cell_style)],
        [Paragraph("<b>Flux Live Dispatch</b>", table_cell_style), Paragraph("WHERE status = ? ORDER BY created_at DESC", code_style), Paragraph("idx_order_status_created", code_style), Paragraph("<b>145.07 ms</b>", table_cell_style), Paragraph("<b>Tri en mémoire éliminé</b> car l'index préserve l'ordre.", table_cell_style)],
        [Paragraph("<b>Garde-fou Webhook</b>", table_cell_style), Paragraph("WHERE idempotency_key = ?", code_style), Paragraph("UNIQUE index", code_style), Paragraph("<b>61.63 ms</b>", table_cell_style), Paragraph("Accès quasi-instantané (0.06 ms/requête).", table_cell_style)],
        [Paragraph("<b>Audit MoMo</b>", table_cell_style), Paragraph("WHERE provider = ? AND status = ?", code_style), Paragraph("logistics_p_provide_idx", code_style), Paragraph("<b>128.29 ms</b>", table_cell_style), Paragraph("Index couvrant sans lire les autres lignes.", table_cell_style)],
    ]
    bench_table = Table(bench_data, colWidths=[90, 130, 105, 75, 85])
    bench_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(bench_table)

    story.append(PageBreak())

    # ==========================================
    # PAGE 4: TESTS, PITCH VIDÉO & CONCLUSION
    # ==========================================
    story.append(Paragraph("6. Validation par les Tests Automatisés (Test Suite)", h1_style))
    story.append(Paragraph(
        "Tous les comportements critiques sont validés par des tests unitaires et d'intégration Django (<code>python manage.py test logistics</code>) :",
        body_style
    ))
    story.append(Paragraph("✔ <code>test_webhook_unauthorized_without_secret</code> : Rejet HTTP 401 si le token secret est absent ou erroné.", bullet_style))
    story.append(Paragraph("✔ <code>test_webhook_successful_payment_and_order_transition</code> : Validation du paiement et bascule automatique de la commande à l'état <code>PAID</code>.", bullet_style))
    story.append(Paragraph("✔ <code>test_webhook_enforces_idempotency_on_duplicates</code> : Vérification qu'un double callback renvoie <code>already_processed</code> sans réinsérer en base.", bullet_style))
    story.append(Paragraph("✔ <code>test_webhook_rejects_underpayment</code> : Détection et blocage d'un montant inférieur à la commande (HTTP 400).", bullet_style))
    story.append(Paragraph("✔ <code>test_driver_order_status_update</code> : Mise à jour par le livreur vers <code>IN_TRANSIT</code> et <code>DELIVERED</code> avec audit.", bullet_style))
    story.append(Paragraph("✔ <code>test_driver_assigned_orders_view</code> : Tri et restitution des commandes assignées optimisés pour faible débit.", bullet_style))
    story.append(Paragraph("<b>Résultat global : 6 tests réussis sur 6 en 0.19 seconde.</b>", body_style))

    story.append(Spacer(1, 15))
    story.append(Paragraph("7. Script Minuté pour la Vidéo de Pitch (3 Minutes Max)", h1_style))
    story.append(Paragraph(
        "Pour la vidéo obligatoire de 3 minutes à joindre au formulaire Google Form, voici le plan d'intervention parfait :",
        body_style
    ))

    pitch_data = [
        [Paragraph("<b>Chrono</b>", table_cell_bold), Paragraph("<b>Sujet à aborder</b>", table_cell_bold), Paragraph("<b>Ce qu'il faut dire face caméra / à l'écran</b>", table_cell_bold)],
        [
            Paragraph("<b>0:00 - 0:30</b>", table_cell_style),
            Paragraph("Introduction & Défi local", table_cell_style),
            Paragraph("<i>« Bonjour au jury AntCode Hub. Je suis Hakimi Yvon. J'ai relevé le Scénario B Track 2. Au Cameroun, l'e-commerce bloque souvent non par manque de clients, mais parce que la logistique et les paiements MoMo s'effondrent face aux coupures réseau et aux adresses informelles. »</i>", table_cell_style)
        ],
        [
            Paragraph("<b>0:30 - 1:15</b>", table_cell_style),
            Paragraph("Architecture & Adresses", table_cell_style),
            Paragraph("<i>« J'ai conçu une architecture Django REST normalisée où les adresses s'appuient sur les quartiers (Akwa, Bastos, Mendong) et des repères visuels réels. Les livreurs ont un endpoint filtré par quartier, très économe en batterie et data pour les téléphones d'entrée de gamme. »</i>", table_cell_style)
        ],
        [
            Paragraph("<b>1:15 - 2:00</b>", table_cell_style),
            Paragraph("Fintech & Idempotence", table_cell_style),
            Paragraph("<i>« Pour MTN MoMo et Orange Money, j'ai implémenté un webhook blindé : clé d'idempotence unique et verrouillage SQL `select_for_update`. Si MTN renvoie 3 fois le même callback à cause d'un lag réseau, le système ne crédite la commande qu'une seule fois. »</i>", table_cell_style)
        ],
        [
            Paragraph("<b>2:00 - 2:40</b>", table_cell_style),
            Paragraph("Benchmark & Indexation", table_cell_style),
            Paragraph("<i>« J'ai généré 500 vraies commandes de test. Mon benchmark prouve que nos index composites éliminent les scans complets de tables et les tris mémoire, maintenant les requêtes sous les 0,15 ms même lors des pics de fin de mois. »</i>", table_cell_style)
        ],
        [
            Paragraph("<b>2:40 - 3:00</b>", table_cell_style),
            Paragraph("Conclusion & Rigueur", table_cell_style),
            Paragraph("<i>« L'IA a servi d'accélérateur comme documenté dans notre Prompt Ledger, mais chaque choix d'architecture a été pensé et validé avec rigueur. Tout est testé et en ligne sur mon GitHub. Merci ! »</i>", table_cell_style)
        ],
    ]
    pitch_table = Table(pitch_data, colWidths=[70, 115, 300])
    pitch_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#EDF2F7")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(pitch_table)

    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=secondary_color, spaceAfter=10))
    story.append(Paragraph(
        "<b>Lien direct vers le dépôt public :</b> <font color='#2B6CB0'><u>https://github.com/hakimi-yvon/antcode-ecommerce-backend</u></font>",
        body_style
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"✅ PDF successfully generated: {pdf_path}")


if __name__ == "__main__":
    build_pdf()
