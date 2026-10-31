# KDP Publishing Studio — version locale

Cette interface est une première application autonome qui utilise les scripts de production de ce dépôt. Elle ne nécessite ni Claude Code, ni compte, ni clé API. Le serveur écoute uniquement sur `127.0.0.1` : il n'est pas exposé sur Internet.

## Compatibilité

- Windows 10/11 64 bits
- Python 3.11 ou plus récent
- Typst installé et accessible dans PATH
- Poppler pour Windows avec `pdfinfo`, `pdftotext`, `pdffonts` et `pdfimages` accessibles dans PATH

Le guide d'installation de Python, Typst et Poppler est dans [windows-setup.md](windows-setup.md).

## Démarrer

1. Téléchargez le dépôt GitHub et extrayez-le dans un dossier permanent.
2. Installez les outils listés ci-dessus.
3. Double-cliquez sur `run-studio.bat`.
4. Le navigateur ouvre `http://127.0.0.1:8765`.
5. Importez un fichier DOCX, TXT ou MD, remplissez les informations et créez le projet.
6. Cliquez sur **Générer les fichiers KDP**.

Les projets sont enregistrés dans `%USERPROFILE%\KDP-Books\`. Les fichiers finaux sont dans le sous-dossier `dist\kdp-upload\` de chaque projet.

## Import des manuscrits

- DOCX : les paragraphes, titres de niveau 1 et 2 et le texte des cellules de tableaux sont importés. Les images, styles complexes, notes et mises en page Word ne sont pas conservés.
- TXT/MD : les paragraphes et titres Markdown `#`, `##`, `###` sont importés. La mise en forme avancée Markdown n'est pas interprétée.
- Le contenu importé est converti en Typst et peut être ajusté dans `manuscript/body.typ`.

## Limites à connaître

Cette première interface est un outil de production, pas un rédacteur de livre. Elle ne rédige pas de texte, ne crée pas de visuels, ne propose pas de mots-clés ou de catégories Amazon et ne publie rien sur votre compte KDP.

Le fichier DOCX est importé comme texte. Pour les livres illustrés, ajoutez et vérifiez les images dans le projet Typst avant la génération. Vérifiez les fichiers PDF dans KDP Print Previewer et commandez une épreuve physique avant publication. Le contrôle automatique ne garantit pas l'acceptation par Amazon.

## Dépannage

Si le statut en haut indique un outil manquant, suivez [windows-setup.md](windows-setup.md), fermez puis relancez le Studio. Les journaux détaillés de chaque étape apparaissent après la génération.
