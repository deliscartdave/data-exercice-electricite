from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

DOSSIER = Path(__file__).parent / "donnees"


@st.cache_data
def lire_consommation_propre(chemin: str) -> pd.DataFrame:
	return pd.read_csv(chemin)


st.set_page_config(page_title="L'électricité dans 12 quartiers", page_icon="⚡", layout="wide")

st.title("L'électricité dans 12 quartiers")
st.caption("Relevés mensuels de janvier 2024 à décembre 2025. Données fictives.")
st.write("Ces relevés mensuels couvrent 12 quartiers de janvier 2024 à décembre 2025.")
st.write("Chaque ligne réunit la consommation, les heures de courant, les informations du quartier et la météo.")

consommation = lire_consommation_propre(str(DOSSIER / "consommation_propre.csv"))
st.write(f"Le fichier nettoyé contient {len(consommation)} lignes.")

communes = sorted(consommation["commune"].dropna().unique().tolist())
communes_selectionnees = st.sidebar.multiselect(
	"Communes",
	options=communes,
	default=communes,
)

annees = sorted(consommation["annee"].dropna().astype(int).unique().tolist())
index_2025 = annees.index(2025) if 2025 in annees else 0
annee_selectionnee = st.sidebar.selectbox(
	"Année",
	options=annees,
	index=index_2025,
)

if communes_selectionnees:
	consommation_filtree = consommation.loc[
		consommation["commune"].isin(communes_selectionnees)
		& (consommation["annee"] == annee_selectionnee)
	]
else:
	consommation_filtree = consommation.iloc[0:0]
	st.info("Sélectionnez au moins une commune pour afficher ses données.")

if consommation_filtree.empty:
	consommation_totale_affichee = "—"
	consommation_par_abonne_affichee = "—"
	heures_moyennes_affichees = "—"
else:
	consommation_totale = consommation_filtree["kwh"].sum()
	consommation_par_abonne = consommation_filtree["kwh_par_abonne"].mean()
	heures_moyennes = consommation_filtree["heures_courant"].mean()
	consommation_totale_affichee = f"{consommation_totale / 1_000_000:.2f}".replace(".", ",") + " M kWh"
	consommation_par_abonne_affichee = f"{consommation_par_abonne:.1f}".replace(".", ",") + " kWh"
	heures_moyennes_affichees = f"{heures_moyennes:.1f}".replace(".", ",") + " h"

colonne_total, colonne_abonne, colonne_heures = st.columns(3)
colonne_total.metric("Consommation totale", consommation_totale_affichee)
colonne_abonne.metric(
	"Consommation moyenne par abonné",
	consommation_par_abonne_affichee,
	help="Moyenne des kWh par abonné des relevés mensuels correspondant aux filtres.",
)
colonne_heures.metric("Heures moyennes d’électricité", heures_moyennes_affichees)

st.caption(f"Lignes correspondant aux filtres : {len(consommation_filtree)}")


def formater_nombre(valeur: float, decimales: int = 1) -> str:
	return f"{valeur:.{decimales}f}".replace(".", ",")


onglet_quartiers, onglet_communes, onglet_correlation, onglet_coupures, onglet_releves = st.tabs(
	[
		"Consommation par quartier",
		"Évolution par commune",
		"Chaleur ou courant ?",
		"Heures de courant",
		"Relevés remarquables",
	]
)

with onglet_quartiers:
	st.subheader("Quels quartiers consomment le plus par abonné ?")
	if consommation_filtree.empty:
		st.info("Aucune donnée à comparer avec les filtres sélectionnés.")
	else:
		moyennes_par_type = (
			consommation_filtree.groupby("type")["kwh_par_abonne"]
			.mean()
			.sort_values(ascending=False)
		)
		classement = (
			consommation_filtree.groupby(["quartier", "type"], as_index=False)["kwh_par_abonne"]
			.mean()
			.sort_values("kwh_par_abonne", ascending=False)
			.reset_index(drop=True)
		)
		fig, ax = plt.subplots(figsize=(9, 5))
		sns.barplot(
			data=classement,
			x="kwh_par_abonne",
			y="quartier",
			hue="type",
			dodge=False,
			palette={"Commercial": "#17684d", "Résidentiel": "#d47a45"},
			ax=ax,
		)
		ax.set_title("Consommation moyenne par abonné et par quartier")
		ax.set_xlabel("kWh par abonné et par mois")
		ax.set_ylabel("")
		ax.legend(title="Type de quartier")
		fig.tight_layout()
		st.pyplot(fig)
		plt.close(fig)
		meilleur_quartier = classement.iloc[0]
		texte_types = " ; ".join(
			f"{type_quartier} : {formater_nombre(moyenne)} kWh/abonné"
			for type_quartier, moyenne in moyennes_par_type.items()
		)
		st.caption(
			f"{texte_types}. En tête : {meilleur_quartier['quartier']} "
			f"({formater_nombre(meilleur_quartier['kwh_par_abonne'])} kWh/abonné)."
		)

with onglet_communes:
	st.subheader("Comment la consommation évolue-t-elle par commune ?")
	if consommation_filtree.empty:
		st.info("Aucune donnée à comparer avec les filtres sélectionnés.")
	else:
		abonnes_par_commune = (
			consommation_filtree.groupby(["commune", "quartier"], as_index=False)["abonnes"]
			.first()
			.groupby("commune")["abonnes"]
			.sum()
		)
		mensuel_par_commune = (
			consommation_filtree.groupby(["commune", "mois"], as_index=False)
			.agg(kwh_total=("kwh", "sum"))
		)
		mensuel_par_commune["kwh_par_abonne"] = (
			mensuel_par_commune["kwh_total"]
			/ mensuel_par_commune["commune"].map(abonnes_par_commune)
		)
		fig, ax = plt.subplots(figsize=(10, 5))
		sns.lineplot(
			data=mensuel_par_commune,
			x="mois",
			y="kwh_par_abonne",
			hue="commune",
			marker="o",
			markersize=3,
			ax=ax,
		)
		ax.set_title(f"Consommation mensuelle par abonné en {annee_selectionnee}")
		ax.set_xlabel("Mois")
		ax.set_ylabel("kWh par abonné")
		ax.tick_params(axis="x", rotation=45)
		ax.legend(title="Commune")
		fig.tight_layout()
		st.pyplot(fig)
		plt.close(fig)
		totaux = consommation_filtree.groupby("commune")["kwh"].sum()
		commune_max = totaux.idxmax()
		st.caption(
			f"En {annee_selectionnee}, {commune_max} totalise le plus de consommation "
			f"parmi les communes sélectionnées : {formater_nombre(totaux[commune_max] / 1_000_000, 2)} millions de kWh."
		)

with onglet_correlation:
	st.subheader("Quelle association observe-t-on entre chaleur, courant et consommation ?")
	if consommation_filtree.empty:
		st.info("Aucune donnée à analyser avec les filtres sélectionnés.")
	else:
		residentiel = consommation_filtree.loc[
			consommation_filtree["type"] == "Résidentiel"
		].copy()
		residentiel_complet = consommation.loc[
			consommation["commune"].isin(communes_selectionnees)
			& (consommation["type"] == "Résidentiel")
		]
		if len(residentiel) < 2:
			st.info("Il faut au moins deux relevés résidentiels pour calculer les corrélations.")
		else:
			correlation_heures = residentiel["kwh_par_abonne"].corr(
				residentiel["heures_courant"]
			)
			correlation_temperature = residentiel["kwh_par_abonne"].corr(
				residentiel["temperature_c"]
			)
			correlation_heures_periode = residentiel_complet["kwh_par_abonne"].corr(
				residentiel_complet["heures_courant"]
			)
			correlation_temperature_periode = residentiel_complet["kwh_par_abonne"].corr(
				residentiel_complet["temperature_c"]
			)
			fig, ax = plt.subplots(figsize=(9, 5))
			sns.scatterplot(
				data=residentiel,
				x="heures_courant",
				y="kwh_par_abonne",
				hue="quartier",
				alpha=0.75,
				s=55,
				ax=ax,
			)
			if residentiel["heures_courant"].nunique() > 1:
				sns.regplot(
					data=residentiel,
					x="heures_courant",
					y="kwh_par_abonne",
					scatter=False,
					color="#263b35",
					line_kws={"linewidth": 2},
					ax=ax,
				)
			ax.set_title(f"Heures de courant et consommation par abonné en {annee_selectionnee}")
			ax.set_xlabel("Heures de courant par jour")
			ax.set_ylabel("kWh par abonné et par mois")
			ax.legend(title="Quartier", bbox_to_anchor=(1.02, 1), loc="upper left")
			fig.tight_layout()
			st.pyplot(fig)
			plt.close(fig)
			st.caption(
				f"Avec les filtres actuels : r = {formater_nombre(correlation_heures, 2)} "
				f"pour les heures et r = {formater_nombre(correlation_temperature, 2)} pour la température. "
				f"Sur toute la période 2024–2025 du notebook : r = "
				f"{formater_nombre(correlation_heures_periode, 2)} et "
				f"{formater_nombre(correlation_temperature_periode, 2)}."
			)

with onglet_coupures:
	st.subheader("Où les heures de courant sont-elles les plus faibles ?")
	if consommation_filtree.empty:
		st.info("Aucune donnée à analyser avec les filtres sélectionnés.")
	else:
		resume_heures = (
			consommation_filtree.groupby("commune")["heures_courant"]
			.agg(
				mediane="median",
				q1=lambda valeurs: valeurs.quantile(0.25),
				q3=lambda valeurs: valeurs.quantile(0.75),
			)
			.sort_values("mediane")
		)
		colonne_boxplot, colonne_histogramme = st.columns(2)
		fig, axes = plt.subplots(1, 2, figsize=(12, 5))
		sns.boxplot(
			data=consommation_filtree,
			x="commune",
			y="heures_courant",
			order=resume_heures.index.tolist(),
			color="#78a992",
			ax=axes[0],
		)
		axes[0].set_title("Heures de courant par commune")
		axes[0].set_xlabel("Commune")
		axes[0].set_ylabel("Heures par jour")
		axes[0].tick_params(axis="x", rotation=20)
		if "Cap-Haïtien" in communes_selectionnees:
			donnees_histogramme = consommation_filtree.loc[
				consommation_filtree["commune"] == "Cap-Haïtien"
			]
			titre_histogramme = "Cap-Haïtien"
		else:
			donnees_histogramme = consommation_filtree
			titre_histogramme = "Communes sélectionnées"
		sns.histplot(
			data=donnees_histogramme,
			x="heures_courant",
			bins=8,
			color="#17684d",
			ax=axes[1],
		)
		axes[1].set_title(f"Distribution des heures : {titre_histogramme}")
		axes[1].set_xlabel("Heures de courant par jour")
		axes[1].set_ylabel("Nombre de relevés")
		fig.tight_layout()
		st.pyplot(fig)
		plt.close(fig)
		commune_mediane_min = resume_heures["mediane"].idxmin()
		st.caption(
			f"La médiane la plus basse est à {commune_mediane_min} : "
			f"{formater_nombre(resume_heures.loc[commune_mediane_min, 'mediane'])} h par jour."
		)

with onglet_releves:
	st.subheader("Quels relevés mensuels présentent les plus fortes consommations ?")
	if consommation_filtree.empty:
		st.info("Aucune donnée à classer avec les filtres sélectionnés.")
	else:
		top3 = consommation_filtree.nlargest(3, "kwh").copy()
		top3["releve"] = top3["quartier"] + " · " + top3["mois"]
		fig, ax = plt.subplots(figsize=(9, 4))
		barres = sns.barplot(
			data=top3,
			x="kwh",
			y="releve",
			color="#17684d",
			ax=ax,
		)
		ax.bar_label(barres.containers[0], fmt="%.0f", padding=5)
		ax.set_title("Trois plus fortes consommations mensuelles")
		ax.set_xlabel("Consommation du quartier (kWh)")
		ax.set_ylabel("")
		fig.tight_layout()
		st.pyplot(fig)
		plt.close(fig)
		meilleur_releve = top3.iloc[0]
		st.caption(
			f"Le maximum parmi les relevés filtrés est {meilleur_releve['quartier']} "
			f"en {meilleur_releve['mois']} : {formater_nombre(meilleur_releve['kwh'], 0)} kWh."
		)

st.markdown(
	"""
### Conclusion générale (2024–2025)

Dans les quartiers résidentiels, les kWh par abonné sont davantage associés aux heures de courant (`r = 0,76`) qu'à la température (`r = -0,15`). Les quartiers commerciaux consomment en moyenne **393,2 kWh par abonné**, contre **117,4** dans les quartiers résidentiels; Centre-ville, Place Saint-Pierre et Delmas 33 sont les trois premiers du classement. La consommation totale de Cap-Haïtien progresse de **4,59 à 5,62 millions de kWh** entre 2024 et 2025 (**+22,46 %**), tandis que Delmas enregistre la plus faible hausse (**+1,10 %**).

**Limites et pistes d'action.** L'analyse couvre seulement deux années et exclut les **9 relevés sans consommation** du fichier brut; les corrélations décrivent une association et ne démontrent pas une cause. La compagnie gagnerait à améliorer la complétude des relevés, suivre plus finement les heures de service et surveiller les quartiers à forte consommation par abonné.
"""
)

with st.expander("Consulter les données filtrées"):
	st.caption(
		f"{len(consommation_filtree)} lignes pour les communes et l'année sélectionnées."
	)
	if consommation_filtree.empty:
		st.info("Aucune ligne ne correspond aux filtres actuels.")
	st.dataframe(consommation_filtree, hide_index=True)
