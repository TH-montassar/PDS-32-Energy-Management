# Use Case détaillé de l'application PDS-32 + trame complète d'un rapport PFE (Tunisie)

## 1) Contexte du projet
PDS-32 est un système IoT de gestion énergétique résidentielle. L'architecture relie un microcontrôleur ESP32 (capteurs + actionneurs), un backend Flask, une base SQLite et un dashboard web. La communication temps réel se fait via MQTT.

Objectif global : **mesurer, analyser, alerter et agir** sur la consommation électrique et le confort (température, humidité, présence, luminosité) pour réduire les coûts et améliorer l'efficacité énergétique.

---

## 2) Description fonctionnelle globale (ce que fait l'application)

### 2.1 Acquisition de données (IoT)
L'ESP32 lit en continu :
- Température / humidité (DHT22)
- Courant électrique (ACS712) pour calculer puissance et énergie
- Présence (PIR)
- Luminosité (LDR)

Puis publie périodiquement via MQTT :
- `home/energy/power`
- `home/sensors/environment`
- `home/sensors/presence`
- `home/actuators/status`
- statut de vie du device `home/status/device`

### 2.2 Traitement backend
Le backend Flask :
- Souscrit aux topics MQTT
- Décode les messages JSON (sauf `home/status/device` en texte)
- Stocke les mesures dans SQLite
- Calcule le coût énergétique (TND/kWh)
- Génère des alertes (haute conso, panne énergie, température anormale)
- Expose des API REST pour le dashboard et le contrôle

### 2.3 Visualisation et pilotage
Le dashboard web affiche :
- Consommation instantanée (W, A, kWh, coût)
- Capteurs environnementaux (T°, humidité, lumière, présence)
- État et commande des actionneurs (HVAC, éclairage, fenêtre, mode auto)
- Analytique (coût du jour, estimation mensuelle, économies potentielles)
- Graphiques 24h et historique
- Alertes avec possibilité de résolution
- Statut LIVE/DOWN de l'ESP32

### 2.4 Automatisation locale intelligente (firmware)
Règles auto embarquées :
- Lumière OFF sans présence
- Lumière ON si présence + faible luminosité
- HVAC ON/OFF selon température et présence
- Fenêtre ouverte/fermée selon humidité
- Mode auto temporairement désactivé lors de commande manuelle, puis réactivé après timeout

---

## 3) Use Case principal (niveau métier)

## Use Case UC-01 : **Superviser et optimiser l'énergie d'une pièce intelligente**

### Acteurs
- **Utilisateur principal** (occupant / gestionnaire logement)
- **ESP32** (acteur technique producteur de données et exécuteur)
- **Backend Flask** (acteur technique d'orchestration)
- **Broker MQTT** (acteur d'échange de messages)

### Préconditions
- ESP32 alimenté, connecté Wi-Fi
- MQTT broker accessible
- Backend Flask lancé
- Dashboard accessible

### Déclencheur
L'utilisateur ouvre le dashboard et/ou le système reçoit de nouvelles mesures MQTT.

### Scénario nominal
1. L'ESP32 mesure capteurs et calcule puissance/énergie.
2. L'ESP32 publie les données sur MQTT.
3. Le backend reçoit et stocke les données dans SQLite.
4. Le backend met à jour alertes et indicateurs analytiques.
5. Le dashboard appelle les API et affiche les valeurs en temps réel (rafraîchissement périodique).
6. L'utilisateur observe consommation, coûts et alertes.
7. Si nécessaire, l'utilisateur envoie une commande (ON/OFF relais, ouverture fenêtre, auto on/off).
8. Le backend relaie la commande via MQTT.
9. L'ESP32 applique la commande et republie l'état actionneurs.
10. Le dashboard reflète l'état réel du système.

### Scénarios alternatifs
- **A1: Perte de connexion ESP32** → statut `DOWN` affiché, dernière activité conservée.
- **A2: Données indisponibles** → API renvoie 404 `No data available`.
- **A3: Commande inconnue** → firmware rejette la commande et n'applique aucun changement.
- **A4: Surcharge consommation** → backend crée alerte `HIGH_CONSUMPTION`.

### Postconditions
- Données historisées
- Commandes tracées via états actionneurs
- Alertes disponibles pour diagnostic
- Décision utilisateur facilitée par KPI

### Règles métier dérivées
- Coût = `energy_total * tarif`.
- Alerte température si `T > 30°C` ou `T < 15°C`.
- Alerte conso si `power > 2000W`.

---

## 4) Use cases détaillés (niveau système)

- **UC-02 Mesurer consommation instantanée**
- **UC-03 Calculer coût énergétique journalier/mensuel estimé**
- **UC-04 Détecter présence et piloter éclairage**
- **UC-05 Réguler confort thermique (HVAC)**
- **UC-06 Gérer humidité via ouverture/fermeture fenêtre**
- **UC-07 Déclencher et résoudre alertes**
- **UC-08 Commander manuellement les actionneurs**
- **UC-09 Basculer mode automatique**
- **UC-10 Produire statistiques horaires/journalières**

---

## 5) Exigences à inclure dans ton rapport PFE

### 5.1 Exigences fonctionnelles
- RF1: Le système doit collecter et publier les mesures toutes les 5 secondes.
- RF2: Le backend doit persister les mesures dans SQLite.
- RF3: Le dashboard doit afficher l'état temps réel des capteurs/actionneurs.
- RF4: L'utilisateur doit pouvoir envoyer des commandes de contrôle.
- RF5: Le système doit gérer les alertes énergétiques et thermiques.
- RF6: Le système doit fournir des statistiques historiques.

### 5.2 Exigences non fonctionnelles
- RNF1: Disponibilité du service web local via Docker.
- RNF2: Temps de rafraîchissement UI ≤ 5 secondes.
- RNF3: Architecture modulaire (Firmware / Backend / Frontend).
- RNF4: Traçabilité minimale des événements via base locale.
- RNF5: Déploiement reproductible via `docker-compose`.

### 5.3 Contraintes
- Broker MQTT public (HiVEMQ)
- Base SQLite locale (pas de cluster distribué)
- Précision capteurs dépend du matériel et calibration

---

## 6) Trame complète recommandée d'un rapport PFE (Tunisie)

> Cette trame suit les pratiques courantes des écoles d'ingénieurs / ISET / FST en Tunisie (adaptable selon cahier des charges de l'établissement).

### Pages préliminaires
1. Page de garde (établissement, spécialité, titre, encadreurs, année)
2. Dédicaces
3. Remerciements
4. Résumé (FR) + Mots-clés
5. Abstract (EN) + Keywords
6. Table des matières
7. Liste des figures
8. Liste des tableaux
9. Liste des acronymes

### Chapitre 1 — Contexte général et problématique
- Contexte énergétique
- Problématique ciblée
- Objectifs généraux et spécifiques
- Méthodologie de travail
- Organisation du rapport

### Chapitre 2 — État de l'art
- Smart home, IoT énergétique, EMS
- Protocoles (MQTT vs HTTP, etc.)
- Technologies comparées (Flask, Node, bases de données)
- Analyse critique des solutions existantes
- Positionnement de votre solution

### Chapitre 3 — Analyse et spécification des besoins
- Identification des acteurs
- Besoins fonctionnels/non fonctionnels
- Diagrammes UML (use case, activités, séquences)
- Scénarios nominaux/alternatifs
- Critères d'acceptation

### Chapitre 4 — Conception
- Architecture globale (IoT + backend + dashboard)
- Modélisation des données (MCD/MLD ou schéma SQL)
- Conception API REST
- Conception des règles d'automatisation
- Choix techniques justifiés

### Chapitre 5 — Réalisation et implémentation
- Firmware ESP32 (capteurs, MQTT, automation)
- Backend Flask (ingestion, API, alertes)
- Dashboard (UI, graphiques, rafraîchissement)
- Conteneurisation Docker
- Captures d'écran et extraits de code essentiels

### Chapitre 6 — Validation, tests et résultats
- Plan de tests (unitaires, intégration, bout-en-bout)
- Scénarios de test réels
- Résultats chiffrés (latence, stabilité, précision)
- Discussion des limites
- Évaluation par rapport aux objectifs

### Chapitre 7 — Conclusion générale et perspectives
- Bilan technique
- Apports personnels et compétences acquises
- Perspectives (IA prédictive, cloud, mobile app, sécurité)

### Annexes
- Guide d'installation
- API détaillée
- Schémas électroniques
- Datasheets capteurs
- Journal de sprint / planning
- Manuel utilisateur

### Bibliographie
- Norme de citation exigée (IEEE/APA selon établissement)
- Références académiques + documentation officielle

---

## 7) Livrables PFE conseillés (Tunisie)

- Rapport final PDF
- Présentation soutenance (slides)
- Code source versionné (Git)
- Démo vidéo (optionnel mais fortement recommandé)
- Manuel utilisateur + manuel technique
- Cahier de tests et résultats
- Poster scientifique (si demandé)

---

## 8) Indicateurs de qualité à présenter dans le rapport

- Fiabilité acquisition capteurs (%)
- Taux de disponibilité backend/dashboard
- Latence commande utilisateur -> actionneur
- Précision estimation coût énergétique
- Nombre d'alertes pertinentes vs fausses alertes
- Gains énergétiques observés (si expérimentation)

---

## 9) Limites actuelles du projet à mentionner honnêtement

- Sécurité MQTT non durcie (broker public, chiffrement absent)
- Base SQLite adaptée prototype mais pas multi-sites
- Absence de gestion fine des rôles/utilisateurs
- Calibration capteurs à approfondir en environnement réel
- Règles auto heuristiques (non prédictives)

---

## 10) Perspectives d'amélioration (section "travaux futurs")

- MQTT TLS + authentification forte
- Passage PostgreSQL + historisation avancée
- Modèles IA de prédiction de charge
- Optimisation basée tarification horaire STEG
- Application mobile + notifications push
- Intégration panneaux PV / batterie / smart meter
- Gestion multi-pièces et multi-bâtiments

---

## 11) Conseils de rédaction PFE (pratiques)

- Écrire en style académique, phrases courtes, schémas lisibles
- Toujours lier un besoin -> une implémentation -> un test -> un résultat
- Éviter les captures floues; privilégier tableaux comparatifs
- Ajouter une conclusion partielle à la fin de chaque chapitre
- Préparer une démonstration "sans internet" si possible

