# apps/ventes_clients/models.py
from django.db import models
from django.utils import timezone
from datetime import date, timedelta
from decimal import Decimal
import qrcode
from io import BytesIO
from django.core.files import File

from users.models import CustomUser
from produits_stocks.models import Product, Lot, Warehouse


# ==================== CLIENT ====================
class Client(models.Model):
    """
    Client / Prospect
    """
    TYPE_CHOICES = (
        ('particulier', 'Particulier'),
        ('entreprise', 'Entreprise'),
        ('revendeur', 'Revendeur'),
        ('grossiste', 'Grossiste'),
    )

    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('inactif', 'Inactif'),
        ('bloque', 'Bloqué'),
    )

    code = models.CharField(max_length=50, unique=True,
                            verbose_name="Code client")
    name = models.CharField(
        max_length=200, verbose_name="Nom / Raison sociale")
    commercial_name = models.CharField(
        max_length=200, blank=True, verbose_name="Nom commercial")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES,
                            default='particulier', verbose_name="Type")
    contact_person = models.CharField(
        max_length=100, blank=True, verbose_name="Personne de contact")
    phone = models.CharField(max_length=20, verbose_name="Téléphone")
    mobile = models.CharField(max_length=20, blank=True, verbose_name="Mobile")
    email = models.EmailField(verbose_name="Email")
    website = models.URLField(blank=True, verbose_name="Site web")
    address = models.TextField(verbose_name="Adresse")
    city = models.CharField(max_length=100, verbose_name="Ville")
    country = models.CharField(
        max_length=100, default='Sénégal', verbose_name="Pays")
    postal_code = models.CharField(
        max_length=20, blank=True, verbose_name="Code postal")
    tax_id = models.CharField(
        max_length=50, blank=True, verbose_name="N° Identification fiscale")
    registration_number = models.CharField(
        max_length=50, blank=True, verbose_name="N° Registre de commerce")

    payment_terms = models.CharField(max_length=20, choices=[
        ('cash', 'Comptant'),
        ('15', '15 jours'),
        ('30', '30 jours'),
        ('45', '45 jours'),
        ('60', '60 jours'),
    ], default='cash', verbose_name="Délai de paiement")

    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Limite de crédit")
    current_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Solde actuel")
    rating = models.DecimalField(
        max_digits=3, decimal_places=2, default=0, verbose_name="Note (0-5)")
    total_purchases = models.DecimalField(
        max_digits=15, decimal_places=2, default=0, verbose_name="Total achats")
    total_orders = models.IntegerField(
        default=0, verbose_name="Nombre de commandes")
    statut = models.CharField(
        max_length=20, choices=STATUT_CHOICES, default='actif', verbose_name="Statut")
    is_favorite = models.BooleanField(
        default=False, verbose_name="Client favori")
    notes = models.TextField(blank=True, verbose_name="Notes")

    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date création")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Date modification")
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Créé par")

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"
        ordering = ['name']

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def full_address(self):
        parts = [self.address, self.city, self.country]
        return ", ".join([p for p in parts if p])


# ==================== DEVIS ====================
class Devis(models.Model):
    """
    Devis / Proforma
    """
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('sent', 'Envoyé'),
        ('accepted', 'Accepté'),
        ('refused', 'Refusé'),
        ('expired', 'Expiré'),
        ('converted', 'Converti en vente'),
    )

    # Identifiants
    devis_number = models.CharField(
        max_length=50, unique=True, verbose_name="N° Devis")

    # Client
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, related_name='devis')
    client_name = models.CharField(max_length=200, verbose_name="Nom client")
    client_phone = models.CharField(
        max_length=20, blank=True, verbose_name="Téléphone client")
    client_email = models.EmailField(blank=True, verbose_name="Email client")
    client_address = models.TextField(
        blank=True, verbose_name="Adresse client")

    # Dates
    devis_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Date devis")
    valid_until = models.DateField(verbose_name="Valable jusqu'au")

    # Montants
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Sous-total")
    discount_type = models.CharField(max_length=20, choices=[
        ('percentage', 'Pourcentage'),
        ('amount', 'Montant')
    ], default='percentage', verbose_name="Type remise")
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Valeur remise")
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Montant remise")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="Taux TVA (%)")
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Montant TVA")
    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Frais de livraison")
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total TTC")

    # Statut
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(
        blank=True, verbose_name="Notes internes")

    # Vente associée (si converti)
    sale = models.ForeignKey('Vente', on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='devis_source')

    # QR Code
    qr_code = models.ImageField(
        upload_to='qrcodes/devis/', null=True, blank=True, verbose_name="QR Code")
    qr_code_data = models.TextField(blank=True, verbose_name="Données QR Code")

    # Métadonnées
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date création")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Date modification")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='devis', verbose_name="Créé par")

    class Meta:
        verbose_name = "Devis"
        verbose_name_plural = "Devis"
        ordering = ['-devis_date']

    def __str__(self):
        return f"{self.devis_number} - {self.client_name}"

    def calculate_totals(self):
        """Calcule les totaux du devis"""
        self.subtotal = sum(line.total for line in self.lignes.all())

        if self.discount_type == 'percentage':
            self.discount_amount = self.subtotal * (self.discount_value / 100)
        else:
            self.discount_amount = self.discount_value

        after_discount = self.subtotal - self.discount_amount
        self.tax_amount = after_discount * (self.tax_rate / 100)
        self.total = after_discount + self.tax_amount + self.shipping_fee
        self.save()

    def generate_qr_code(self):
        """Génère un QR Code pour le devis"""
        if not self.devis_number:
            return

        import json
        qr_data = {
            'type': 'devis',
            'id': self.id,
            'number': self.devis_number,
            'client': self.client_name,
            'total': str(self.total),
            'date': self.devis_date.strftime('%Y-%m-%d %H:%M:%S'),
            'valid_until': self.valid_until.strftime('%Y-%m-%d'),
            'status': self.status,
            'url': f'/devis/{self.id}/'
        }

        qr_data_str = json.dumps(qr_data, ensure_ascii=False)
        self.qr_code_data = qr_data_str

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_str)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')

        filename = f"qr_devis_{self.devis_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_code or not self.qr_code_data:
            self.generate_qr_code()
            super().save(update_fields=['qr_code', 'qr_code_data'])

    def convert_to_sale(self, user=None):
        """
        Convertit le devis en vente
        """
        from .models import Vente, LigneVente

        # Générer le numéro de facture
        last_vente = Vente.objects.order_by('-id').first()
        if last_vente and last_vente.invoice_number:
            try:
                num = int(last_vente.invoice_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        invoice_number = f"INV-{date.today().year}-{num:04d}"

        # Créer la vente
        vente = Vente.objects.create(
            invoice_number=invoice_number,
            client=self.client,
            client_name=self.client_name,
            client_phone=self.client_phone,
            client_email=self.client_email,
            client_address=self.client_address,
            payment_due_date=date.today() + timedelta(days=30),
            subtotal=self.subtotal,
            discount_type=self.discount_type,
            discount_value=self.discount_value,
            discount_amount=self.discount_amount,
            tax_rate=self.tax_rate,
            tax_amount=self.tax_amount,
            shipping_fee=self.shipping_fee,
            total=self.total,
            notes=self.notes,
            internal_notes=self.internal_notes,
            status='draft',
            created_by=user
        )

        # Copier les lignes
        for ligne_devis in self.lignes.all():
            LigneVente.objects.create(
                sale=vente,
                product=ligne_devis.product,
                quantity=ligne_devis.quantity,
                unit_price=ligne_devis.unit_price,
                discount=ligne_devis.discount,
                tax_rate=ligne_devis.tax_rate,
                total=ligne_devis.total,
                notes=ligne_devis.notes
            )

        # Mettre à jour le statut du devis
        self.status = 'converted'
        self.sale = vente
        self.save()

        # Calculer les totaux de la vente
        vente.calculate_totals()
        vente.generate_qr_code()
        vente.save()

        return vente


# ==================== LIGNE DEVIS ====================
class LigneDevis(models.Model):
    """
    Ligne de devis
    """
    devis = models.ForeignKey(
        Devis, on_delete=models.CASCADE, related_name='lignes')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    quantity = models.IntegerField(verbose_name="Quantité")
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prix unitaire")
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Remise")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="TVA (%)")
    total = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Total ligne")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Ligne de devis"
        verbose_name_plural = "Lignes de devis"

    def __str__(self):
        return f"{self.devis.devis_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount
        super().save(*args, **kwargs)
        self.devis.calculate_totals()


# ==================== VENTE ====================
class Vente(models.Model):
    """
    Vente / Bon de commande client
    """
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmée'),
        ('paid', 'Payée'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('returned', 'Retournée'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'En attente'),
        ('partial', 'Paiement partiel'),
        ('paid', 'Payé'),
    )

    # Identifiants
    invoice_number = models.CharField(
        max_length=50, unique=True, verbose_name="N° Facture")
    order_number = models.CharField(
        max_length=50, unique=True, null=True, blank=True, verbose_name="N° Commande")

    # Client
    client = models.ForeignKey(
        Client, on_delete=models.SET_NULL, null=True, related_name='sales')
    client_name = models.CharField(max_length=200, verbose_name="Nom client")
    client_phone = models.CharField(
        max_length=20, blank=True, verbose_name="Téléphone client")
    client_email = models.EmailField(blank=True, verbose_name="Email client")
    client_address = models.TextField(
        blank=True, verbose_name="Adresse client")

    # Dates
    sale_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Date vente")
    delivery_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Date livraison")
    payment_due_date = models.DateField(verbose_name="Date échéance paiement")

    # Montants
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Sous-total")
    discount_type = models.CharField(max_length=20, choices=[
        ('percentage', 'Pourcentage'),
        ('amount', 'Montant')
    ], default='percentage', verbose_name="Type remise")
    discount_value = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Valeur remise")
    discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Montant remise")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="Taux TVA (%)")
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Montant TVA")
    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Frais de livraison")
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total TTC")

    # Paiement
    payment_method = models.CharField(
        max_length=50, blank=True, verbose_name="Méthode de paiement")
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending', verbose_name="Statut paiement")
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Montant payé")
    amount_due = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Montant dû")

    # Livraison
    delivery_method = models.CharField(
        max_length=50, blank=True, verbose_name="Méthode de livraison")
    delivery_address = models.TextField(
        blank=True, null=True, verbose_name="Adresse de livraison")
    delivery_status = models.CharField(
        max_length=50, default='pending', verbose_name="Statut livraison")
    tracking_number = models.CharField(
        max_length=100, blank=True, verbose_name="N° de suivi")

    # Statut
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")
    notes = models.TextField(blank=True, verbose_name="Notes")
    internal_notes = models.TextField(
        blank=True, verbose_name="Notes internes")

    # QR Code
    qr_code = models.ImageField(
        upload_to='qrcodes/sales/', null=True, blank=True, verbose_name="QR Code")
    qr_code_data = models.TextField(blank=True, verbose_name="Données QR Code")

    # Métadonnées
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="Date création")
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name="Date modification")
    created_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='sales', verbose_name="Créé par")

    class Meta:
        verbose_name = "Vente"
        verbose_name_plural = "Ventes"
        ordering = ['-sale_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.client_name}"

    def calculate_totals(self):
        """Calcule les totaux de la vente"""
        self.subtotal = sum(line.total for line in self.lines.all())

        if self.discount_type == 'percentage':
            self.discount_amount = self.subtotal * (self.discount_value / 100)
        else:
            self.discount_amount = self.discount_value

        after_discount = self.subtotal - self.discount_amount
        self.tax_amount = after_discount * (self.tax_rate / 100)
        self.total = after_discount + self.tax_amount + self.shipping_fee
        self.amount_due = self.total - self.amount_paid

        if self.amount_due <= 0:
            self.payment_status = 'paid'
        elif self.amount_paid > 0:
            self.payment_status = 'partial'
        else:
            self.payment_status = 'pending'

        self.save()

    def generate_qr_code(self):
        """Génère un QR Code pour la vente"""
        if not self.invoice_number:
            return

        import json
        qr_data = {
            'type': 'sale',
            'id': self.id,
            'number': self.invoice_number,
            'client': self.client_name,
            'total': str(self.total),
            'date': self.sale_date.strftime('%Y-%m-%d %H:%M:%S'),
            'status': self.status,
            'url': f'/ventes/{self.id}/'
        }

        qr_data_str = json.dumps(qr_data, ensure_ascii=False)
        self.qr_code_data = qr_data_str

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_str)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')

        filename = f"qr_sale_{self.invoice_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        """Sauvegarde la vente et génère automatiquement une facture si confirmée"""
        if self.pk:
            try:
                old_vente = Vente.objects.get(pk=self.pk)
                old_status = old_vente.status
            except Vente.DoesNotExist:
                old_status = None
        else:
            old_status = None

        super().save(*args, **kwargs)

        if not self.qr_code or not self.qr_code_data:
            self.generate_qr_code()
            super().save(update_fields=['qr_code', 'qr_code_data'])

        if old_status != 'confirmed' and self.status == 'confirmed':
            self._generate_invoice()

    def _generate_invoice(self):
        """Génère automatiquement une facture lorsque la vente est confirmée"""
        from .models import Facture

        if Facture.objects.filter(sale=self).exists():
            return

        due_date = date.today() + timedelta(days=30)

        last_facture = Facture.objects.order_by('-id').first()
        if last_facture and last_facture.invoice_number:
            try:
                num = int(last_facture.invoice_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        invoice_number = f"FAC-{date.today().year}-{num:04d}"

        facture = Facture.objects.create(
            invoice_number=invoice_number,
            sale=self,
            client=self.client,
            due_date=due_date,
            subtotal=self.subtotal,
            tax_amount=self.tax_amount,
            total=self.total,
            status='sent',
            notes=f"Facture générée automatiquement depuis la vente {self.invoice_number}"
        )

        facture.generate_qr_code()
        facture.save()

        return facture


# ==================== LIGNE VENTE ====================
class LigneVente(models.Model):
    """
    Ligne de vente
    """
    sale = models.ForeignKey(
        Vente, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    lot = models.ForeignKey(
        Lot, on_delete=models.SET_NULL, null=True, blank=True)

    quantity = models.IntegerField(verbose_name="Quantité")
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Prix unitaire")
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Remise")
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, verbose_name="TVA (%)")
    total = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Total ligne")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Ligne de vente"
        verbose_name_plural = "Lignes de vente"

    def __str__(self):
        return f"{self.sale.invoice_number} - {self.product.name}"

    def save(self, *args, **kwargs):
        self.total = (self.quantity * self.unit_price) - self.discount
        super().save(*args, **kwargs)
        self.sale.calculate_totals()


# ==================== FACTURE ====================
class Facture(models.Model):
    """
    Facture client
    """
    STATUS_CHOICES = (
        ('draft', 'Brouillon'),
        ('sent', 'Envoyée'),
        ('paid', 'Payée'),
        ('overdue', 'En retard'),
        ('cancelled', 'Annulée'),
        ('partial', 'Partiellement payée'),
    )

    invoice_number = models.CharField(
        max_length=50, unique=True, verbose_name="N° Facture")
    sale = models.ForeignKey(
        Vente, on_delete=models.CASCADE, related_name='invoices')
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='invoices')

    invoice_date = models.DateField(
        auto_now_add=True, verbose_name="Date facture")
    due_date = models.DateField(verbose_name="Date échéance")

    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Sous-total")
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="TVA")
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Total")
    amount_paid = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Montant payé")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='draft', verbose_name="Statut")

    pdf_file = models.FileField(
        upload_to='invoices/', null=True, blank=True, verbose_name="PDF facture")
    notes = models.TextField(blank=True, verbose_name="Notes")

    qr_code = models.ImageField(
        upload_to='qrcodes/invoices/', null=True, blank=True, verbose_name="QR Code")
    qr_code_data = models.TextField(blank=True, verbose_name="Données QR Code")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Facture"
        verbose_name_plural = "Factures"
        ordering = ['-invoice_date']

    def __str__(self):
        return f"{self.invoice_number} - {self.client.name}"

    @property
    def remaining_amount(self):
        return self.total - self.amount_paid

    def generate_qr_code(self):
        """Génère un QR Code pour la facture"""
        if not self.invoice_number:
            return

        import json
        qr_data = {
            'type': 'invoice',
            'id': self.id,
            'number': self.invoice_number,
            'client': self.client.name,
            'total': str(self.total),
            'date': self.invoice_date.strftime('%Y-%m-%d'),
            'due_date': self.due_date.strftime('%Y-%m-%d'),
            'status': self.status,
            'url': f'/factures/{self.id}/'
        }

        qr_data_str = json.dumps(qr_data, ensure_ascii=False)
        self.qr_code_data = qr_data_str

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_str)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')

        filename = f"qr_invoice_{self.invoice_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.qr_code or not self.qr_code_data:
            self.generate_qr_code()
            super().save(update_fields=['qr_code', 'qr_code_data'])


# ==================== PAIEMENT ====================
class Paiement(models.Model):
    """
    Paiement client - Lié à une facture
    """
    METHOD_CHOICES = (
        ('cash', 'Espèces'),
        ('card', 'Carte bancaire'),
        ('check', 'Chèque'),
        ('transfer', 'Virement'),
        ('mobile_money', 'Mobile Money'),
        ('credit', 'Crédit'),
    )

    facture = models.ForeignKey(
        'Facture', on_delete=models.CASCADE, related_name='paiements', verbose_name="Facture")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Montant")
    method = models.CharField(
        max_length=20, choices=METHOD_CHOICES, verbose_name="Méthode")
    reference = models.CharField(
        max_length=100, blank=True, verbose_name="Référence")
    payment_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Date paiement")
    received_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, verbose_name="Reçu par")
    notes = models.TextField(blank=True, verbose_name="Notes")

    qr_code = models.ImageField(
        upload_to='qrcodes/payments/', null=True, blank=True, verbose_name="QR Code")
    qr_code_data = models.TextField(blank=True, verbose_name="Données QR Code")

    class Meta:
        verbose_name = "Paiement"
        verbose_name_plural = "Paiements"
        ordering = ['-payment_date']

    def __str__(self):
        return f"{self.facture.invoice_number} - {self.amount} FCFA"

    def generate_qr_code(self):
        """Génère un QR Code pour le paiement"""
        import json
        from io import BytesIO
        from django.core.files import File
        import qrcode

        qr_data = {
            'type': 'payment',
            'id': self.id,
            'amount': str(self.amount),
            'method': self.method,
            'client': self.facture.client.name,
            'invoice': self.facture.invoice_number,
            'date': self.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
            'reference': self.reference or '',
            'url': f'/paiements/{self.id}/'
        }

        qr_data_str = json.dumps(qr_data, ensure_ascii=False)
        self.qr_code_data = qr_data_str

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data_str)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format='PNG')

        filename = f"qr_payment_{self.id}_{self.facture.invoice_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)

    def save(self, *args, **kwargs):
        from decimal import Decimal
        from django.db.models import Sum

        super().save(*args, **kwargs)

        if not self.qr_code or not self.qr_code_data:
            self.generate_qr_code()
            super().save(update_fields=['qr_code', 'qr_code_data'])

        total_paid = self.facture.paiements.aggregate(
            total=Sum('amount'))['total'] or Decimal('0')
        self.facture.amount_paid = total_paid

        if self.facture.amount_paid >= self.facture.total:
            self.facture.status = 'paid'
        elif self.facture.amount_paid > 0:
            self.facture.status = 'partial'
        self.facture.save()

        sale = self.facture.sale
        if sale:
            total_paid_sale = sum(f.amount_paid for f in sale.invoices.all())
            sale.amount_paid = total_paid_sale
            sale.amount_due = sale.total - sale.amount_paid

            if sale.amount_due <= 0:
                sale.payment_status = 'paid'
            elif sale.amount_paid > 0:
                sale.payment_status = 'partial'
            else:
                sale.payment_status = 'pending'
            sale.save()


# ==================== AVOIR ====================
class Avoir(models.Model):
    """
    Avoir / Note de crédit
    """
    TYPE_CHOICES = (
        ('credit', 'Avoir'),
        ('debit', 'Note de débit'),
    )

    avoir_number = models.CharField(
        max_length=50, unique=True, verbose_name="N° Avoir")
    sale = models.ForeignKey(
        Vente, on_delete=models.CASCADE, related_name='credits')
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name='credits')
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='credit', verbose_name="Type")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Montant")
    reason = models.TextField(verbose_name="Raison")
    date = models.DateField(auto_now_add=True, verbose_name="Date")
    notes = models.TextField(blank=True, verbose_name="Notes")
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True, verbose_name="Créé par")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avoir"
        verbose_name_plural = "Avoirs"
        ordering = ['-date']

    def __str__(self):
        return f"{self.avoir_number} - {self.client.name} - {self.amount} FCFA"


# ==================== TAXE ====================
class Taxe(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    rate = models.DecimalField(
        max_digits=5, decimal_places=2, verbose_name="Taux (%)")
    is_default = models.BooleanField(default=False, verbose_name="Par défaut")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Taxe"
        verbose_name_plural = "Taxes"

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


# ==================== REMISE ====================
class Remise(models.Model):
    TYPE_CHOICES = (
        ('percentage', 'Pourcentage'),
        ('amount', 'Montant fixe'),
    )

    name = models.CharField(max_length=100, verbose_name="Nom")
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, verbose_name="Type")
    value = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Valeur")
    min_purchase = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Achat minimum")
    start_date = models.DateField(
        null=True, blank=True, verbose_name="Date début")
    end_date = models.DateField(null=True, blank=True, verbose_name="Date fin")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    clients = models.ManyToManyField(
        Client, blank=True, verbose_name="Clients concernés")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Remise"
        verbose_name_plural = "Remises"

    def __str__(self):
        return f"{self.name} - {self.value}{'%' if self.type == 'percentage' else ' FCFA'}"


# ==================== POINT DE VENTE ====================
class PointDeVente(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom")
    code = models.CharField(max_length=20, unique=True, verbose_name="Code")
    warehouse = models.ForeignKey(
        Warehouse, on_delete=models.SET_NULL, null=True, verbose_name="Entrepôt associé")
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Point de vente"
        verbose_name_plural = "Points de vente"

    def __str__(self):
        return self.name


# ==================== SESSION CAISSE ====================
class SessionCaisse(models.Model):
    STATUS_CHOICES = (
        ('open', 'Ouverte'),
        ('closed', 'Fermée'),
        ('suspended', 'Suspendue'),
    )

    point_de_vente = models.ForeignKey(
        PointDeVente, on_delete=models.CASCADE, related_name='sessions')
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='cash_sessions')
    opening_date = models.DateTimeField(
        auto_now_add=True, verbose_name="Date ouverture")
    closing_date = models.DateTimeField(
        null=True, blank=True, verbose_name="Date fermeture")
    opening_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Solde d'ouverture")
    closing_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Solde de fermeture")
    expected_balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Solde attendu")
    difference = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Différence")
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='open', verbose_name="Statut")
    notes = models.TextField(blank=True, verbose_name="Notes")

    class Meta:
        verbose_name = "Session de caisse"
        verbose_name_plural = "Sessions de caisse"
        ordering = ['-opening_date']

    def __str__(self):
        return f"{self.point_de_vente.name} - {self.user.email} - {self.opening_date}"


# ==================== MOUVEMENT CAISSE ====================
class MouvementCaisse(models.Model):
    TYPE_CHOICES = (
        ('sale', 'Vente'),
        ('payment', 'Paiement'),
        ('deposit', 'Dépôt'),
        ('withdrawal', 'Retrait'),
        ('expense', 'Dépense'),
    )

    session = models.ForeignKey(
        SessionCaisse, on_delete=models.CASCADE, related_name='movements')
    type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, verbose_name="Type")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name="Montant")
    description = models.CharField(max_length=200, verbose_name="Description")
    reference = models.CharField(
        max_length=100, blank=True, verbose_name="Référence")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        CustomUser, on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Mouvement de caisse"
        verbose_name_plural = "Mouvements de caisse"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - {self.amount} FCFA"
