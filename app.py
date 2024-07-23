import streamlit as st
import pandas as pd
import polars as pl
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="ASC - TDB Lundi",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://docs.streamlit.io/',
        #'Report a bug': "rafi.rashid-abdur@service-civique.gouv.fr",
        'About': "This app allows to quickly calculate KPIs for Monday's dashboard."
    }
)

# CONTRATS SAISIS ------------------------------------------------------------------------------------------------------------------------------------------------
st.title('Contrats Saisis')
st.markdown("<hr>", unsafe_allow_html=True)

uploaded_file_1 = st.file_uploader("Choisissez le fichier CSV des contrats saisis", type="csv", key = "saisis")
    
if uploaded_file_1 is not None:

    # Data importation
    contrat_saisis = pl.read_csv(uploaded_file_1, encoding="latin1", separator=';')
    contrat_saisis = contrat_saisis.to_pandas()

    with st.expander("Aperçu des données:"):
        st.dataframe(contrat_saisis.head())
             
    # Data transformation
    contrat_saisis = contrat_saisis.assign(
        **{col: pd.to_datetime(contrat_saisis[col], format="%d/%m/%Y", errors='coerce').dt.date for col in contrat_saisis.columns if "DATE" in col},
        **{col: contrat_saisis[col].astype(str) for col in contrat_saisis.columns if col.startswith("CODE_POST") or col.startswith("CODEPOSTAL")},
        CTV_NUM_AVENANT = contrat_saisis['CTV_NUM_AVENANT'].astype(str),
        Date_vrai_fin = np.where(contrat_saisis['CTV_DATE_EFFET_RUPTURE'].isna(), contrat_saisis['CTV_DATE_FIN_PREV'], contrat_saisis['CTV_DATE_EFFET_RUPTURE']),    
    )

    contrat_saisis = contrat_saisis.assign(
        **{col: pd.to_datetime(contrat_saisis[col], format="%d/%m/%Y", errors='coerce').dt.date for col in contrat_saisis.columns if "Date" in col},
        Annee_vrai_fin = pd.to_datetime(contrat_saisis['Date_vrai_fin'], dayfirst=True).dt.year.astype(str),
        Mois_debut = pd.to_datetime(contrat_saisis['CTV_DATE_DEBUT'], dayfirst=True).dt.month.astype(str),
        Annee_debut = pd.to_datetime(contrat_saisis['CTV_DATE_DEBUT'], dayfirst=True).dt.year.astype(str)
    )
     
    with st.expander("Données transformées:"):
        st.dataframe(contrat_saisis.head())

    # Date imput
    date_du_jour = st.date_input("Sélectionnez la date du jour", datetime.today())

    # Metrics
    ## En cours de mission
    en_cours_mission = contrat_saisis[(contrat_saisis['CTV_DATE_DEBUT'] <= date_du_jour) & (contrat_saisis['Date_vrai_fin'] >= date_du_jour)].shape[0]

    ## Contrats saisis à date en 2024
    contrats_2024 = contrat_saisis[contrat_saisis['Annee_debut'] == "2024"].shape[0]

    ## Janvier-Aout
    jan_aout = contrat_saisis[(contrat_saisis['Annee_debut'] == "2024") & (contrat_saisis['Mois_debut'].isin(["1", "2", "3", "4", "5", "6", "7", "8"]))].shape[0]

    ## Septembre-Decembre
    sept_dec = contrat_saisis[(contrat_saisis['Annee_debut'] == "2024") & (contrat_saisis['Mois_debut'].isin(["9", "10", "11", "12"]))].shape[0]

    # Metrics layout
    st.metric(label="Contrats en cours de mission :", value= en_cours_mission)

    col1, col2, col3 = st.columns(3)
        
    with col1:
        st.metric(label="Contrats saisis à date en 2024 :", value= contrats_2024)
        
    with col2:
        st.metric(label="Contrats saisis de janvier à août 2024 :", value= jan_aout)
        
    with col3:
        st.metric(label="Contrats saisis de septembre à décembre 2024 :", value= sept_dec)
        
    # Graphique Plotly pour les contrats saisis par mois
    mois_label = {1: 'Janvier', 2: 'Février', 3: 'Mars', 4: 'Avril', 5: 'Mai', 6: 'Juin',
                  7: 'Juillet', 8: 'Août', 9: 'Septembre', 10: 'Octobre', 11: 'Novembre', 12: 'Décembre'}

    contrats_par_mois = contrat_saisis[contrat_saisis['Annee_debut'] == "2024"].groupby('Mois_debut').size().reset_index(name='count')
    contrats_par_mois['Mois_debut'] = contrats_par_mois['Mois_debut'].astype(int)
    contrats_par_mois = contrats_par_mois.sort_values(by='Mois_debut')
    contrats_par_mois['Mois_debut'] = contrats_par_mois['Mois_debut'].map(mois_label)

    fig = px.bar(contrats_par_mois, 
                 x='Mois_debut', 
                 y='count', 
                 title="Contrats saisis par mois en 2024", 
                 labels={'Mois_debut': 'Mois', 'count': 'Nombre de contrats saisis'}, 
                 color_discrete_sequence=['#ADD8E6'],
                 hover_data={'Mois_debut': False, 'count': True})
    fig.update_traces(hovertemplate='<b>%{x}</b><br>Contrats: %{y}')
    st.plotly_chart(fig)


st.markdown("<br><br>", unsafe_allow_html=True)

# OSCAR ---------------------------------------------------------------------------------------------------------------------------------------------------------
st.title('OSCAR')
st.markdown("<hr>", unsafe_allow_html=True)

uploaded_file_2 = st.file_uploader("Choisissez le fichier Excel de l'export OSCAR", type="xlsx", key = "oscar")
    
if uploaded_file_2 is not None:

    # Data importation
    oscar = pl.read_excel(uploaded_file_2, sheet_name = "Détails", read_options={"header_row": 1})
    oscar = oscar.to_pandas()

    with st.expander("Aperçu des données:"):
        st.dataframe(oscar.head())
             
    oscar["National_ou_local"] = oscar["N° d'Agrément"].apply(lambda x: "National" if str(x).startswith("NA") else "Local")

    # Calculer les sommes mensuelles pour les postes agréés au local et au national
    postes_agrees = oscar[oscar["Statut de la Demande"] == "DOSSIER_ACCEPTE"].groupby("National_ou_local").sum()

    # Garder uniquement les colonnes des mois
    mois = ['Jan', 'Fev', 'Mars', 'Avril', 'Mai', 'Juin', 'Jui', 'Août', 'Sept', 'Oct', 'Nov', 'Déc']
    postes_agrees = postes_agrees[mois]

    # Transposer les résultats pour obtenir les mois en lignes
    postes_agrees = postes_agrees.T

    # Renommer les colonnes pour clarifier
    postes_agrees.columns = ["Postes agréés au local", "Postes agréés au national"]

    st.header("Onglet « Taux de réalisation »")
    st.write(postes_agrees)

    # Graphique Plotly pour les postes agrées par mois
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(x=postes_agrees.index, y=postes_agrees["Postes agréés au local"], name='Postes agréés au local', marker_color='#ADD8E6',hovertemplate='<b>%{x}</b><br>Postes locaux: %{y}'))
    fig2.add_trace(go.Bar(x=postes_agrees.index, y=postes_agrees["Postes agréés au national"], name='Postes agréés au national', marker_color='#87CEFA',hovertemplate='<b>%{x}</b><br>Postes locaux: %{y}'))

    fig2.update_layout(barmode='group', title="Postes agréés par mois", xaxis_title="Mois", yaxis_title="Nombre de postes agréés")
    st.plotly_chart(fig2)

st.markdown("<br><br>", unsafe_allow_html=True)

# CONTRATS VALIDES ------------------------------------------------------------------------------------------------------------------------------------------------
st.title('Base volontaire')
st.markdown("<hr>", unsafe_allow_html=True)

@st.cache_data
def load_base_volontaire(uploaded_base_stable, uploaded_contrats_valides):

    # Charger la base stable avec polars
    base_stable = pl.read_excel(uploaded_base_stable, sheet_name="Data")
    base_stable = base_stable.drop(['Colonne1', 'Colonne2', 'Colonne3', 'Colonne4']).to_pandas()

    # Charger les contrats valides avec pandas
    contrat_valides = pd.read_csv(uploaded_contrats_valides, encoding="latin1", sep=';')

    # Concaténer la base stable et les contrats validés
    base_volontaire = pd.concat([base_stable,contrat_valides], join='outer', ignore_index=True)

    # Transformation des données
    base_volontaire = base_volontaire.assign(
    **{col: pd.to_datetime(base_volontaire[col], format="%d/%m/%Y", errors='coerce').dt.date for col in base_volontaire.columns if "DATE" in col},
    **{col: base_volontaire[col].apply(lambda x: None if pd.isna(x) else str(int(x))) for col in base_volontaire.columns if col.startswith("CODE_POST") or col.startswith("CODEPOSTAL")},
    CTV_NUM_AVENANT = base_volontaire['CTV_NUM_AVENANT'].astype(str),
    DEVOIRS_FAITS = base_volontaire['DEVOIRS_FAITS'].combine_first(base_volontaire['Devoirs Faits']),
    EVENEMENT_SPORTIF_MAJEUR = base_volontaire['EVENEMENT_SPORTIF_MAJEUR'].combine_first(base_volontaire['évènement sportif majeur']),
    Date_vrai_fin = np.where(base_volontaire['CTV_DATE_EFFET_RUPTURE'].isna(), base_volontaire['CTV_DATE_FIN_PREV'], base_volontaire['CTV_DATE_EFFET_RUPTURE']),    
    )
    
    base_volontaire.drop(columns=['évènement sportif majeur', 'Devoirs Faits'], inplace=True)

    base_volontaire = base_volontaire.assign(
        **{col: pd.to_datetime(base_volontaire[col], format="%d/%m/%Y", errors='coerce').dt.date for col in base_volontaire.columns if "Date" in col},
        Annee_vrai_fin = pd.to_datetime(base_volontaire['Date_vrai_fin'], dayfirst=True).dt.year.astype(str),
        Mois_debut = pd.to_datetime(base_volontaire['CTV_DATE_DEBUT'], dayfirst=True).dt.month.astype(str),
        Annee_debut = pd.to_datetime(base_volontaire['CTV_DATE_DEBUT'], dayfirst=True).dt.year.astype(str),
        National_ou_local = np.where(base_volontaire['AGR_NUMERO'].str[:2] == "NA", "National", "Local"),
        Rupture = np.where(base_volontaire['CTV_DATE_EFFET_RUPTURE'].isna(), 0, 1)
    )

    return base_volontaire

# Upload des fichiers et calcul des KPI
uploaded_base_stable = st.file_uploader("Choisissez le fichier Excel de la base stable", type="xlsx", key="base_stable")
uploaded_contrats_valides = st.file_uploader("Choisissez le fichier CSV des contrats validés", type="csv", key="contrats_valides")

if uploaded_base_stable and uploaded_contrats_valides:
    if st.button('Charger les données'):
        with st.spinner('Chargement des données...'):

            data = load_base_volontaire(uploaded_base_stable, uploaded_contrats_valides)  

            with st.expander("Aperçu des données:"):
                st.dataframe(data.tail())

            mois_label = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin','Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre']

            # Contrats nationaux et locaux
            contrats_nat_loc = data[data["Annee_debut"] == "2024"].groupby(["Mois_debut", "National_ou_local"]).size().reset_index(name='count').pivot(index='Mois_debut', columns='National_ou_local', values='count').fillna(0)    
            contrats_nat_loc = contrats_nat_loc.sort_index(key=lambda x: x.str.zfill(2)).reset_index()
            contrats_nat_loc.columns = ["Mois_debut", "Contrats locaux", "Contrats nationaux"]
            contrats_nat_loc = contrats_nat_loc.assign(Mois_debut = contrats_nat_loc['Mois_debut'].astype(int).map(lambda x: mois_label[x - 1]))

            # Contrats 2024
            contrats_2024 = data[data["Annee_debut"] == "2024"].groupby('Mois_debut').size().reset_index(name='count')      
            contrats_2024['Mois_debut'] = contrats_2024['Mois_debut'].astype(int)  
            contrats_2024 = contrats_2024.sort_values(by='Mois_debut').assign(Mois_debut = contrats_2024['Mois_debut'].map(lambda x: mois_label[x - 1])).reset_index(drop=True)
            contrats_2024.columns = ["Mois", "2024"]
           
            # Contrats 2023
            contrats_2023 = data[data["Annee_debut"] == "2023"].groupby('Mois_debut').size().reset_index(name='count')           
            contrats_2023['Mois_debut'] = contrats_2023['Mois_debut'].astype(int)  # Convertir en int pour le tri numérique
            contrats_2023 = contrats_2023.sort_values(by='Mois_debut').assign(Mois_debut = contrats_2023['Mois_debut'].map(lambda x: mois_label[x - 1])).reset_index(drop=True)
            contrats_2023.columns = ["Mois", "2023"]

            # KPI
            nb_vsc = data.shape[0]
            stock_1er_janvier = data[(data["Annee_debut"] == "2023") & (data["Annee_vrai_fin"] == "2024")].shape[0]
            flux_2024 = data[data["Annee_debut"] == "2024"].shape[0]
            flux_2023 = data[data["Annee_debut"] == "2023"].shape[0]

            # Affichage KPI           
            st.header("Onglet « Cadrage »")
            
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(label="Nombre de VSC depuis 2010",value=nb_vsc)
                st.metric(label="Flux 2024",value=flux_2024)
                st.write(contrats_2024)

            with col2:
                st.metric(label="Stock au 1er janvier 2024",value=stock_1er_janvier)
                st.metric(label="Flux 2023",value=flux_2023)
                st.write(contrats_2023)

            st.header("Onglet « Taux de réalisation »")
            st.write(contrats_nat_loc)

            fig3 = go.Figure()
            fig3.add_trace(go.Bar(x=contrats_nat_loc['Mois_debut'], y=contrats_nat_loc["Contrats locaux"], name='Contrats locaux', marker_color='#ADD8E6', hovertemplate='<b>%{x}</b><br>Contrats locaux: %{y}'))
            fig3.add_trace(go.Bar(x=contrats_nat_loc['Mois_debut'], y=contrats_nat_loc["Contrats nationaux"], name='Contrats nationaux', marker_color='#87CEFA', hovertemplate='<b>%{x}</b><br>Contrats nationaux: %{y}'))

            fig3.update_layout(barmode='group', title="Contrats nationaux et locaux par mois en 2024", xaxis_title="Mois", yaxis_title="Nombre de contrats")
            st.plotly_chart(fig3)

