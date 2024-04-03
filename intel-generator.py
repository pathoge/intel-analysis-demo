import json
import logging
import random
from datetime import datetime, timedelta
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk, BulkIndexError



NUM_REPORTS = 10000
CLOUD_ID = ""
USER = ""
PASSWORD = ""
INDEX = "intel-reports"

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("elasticsearch").setLevel(logging.WARNING)
logging.getLogger("elastic_transport").setLevel(logging.WARNING)


def setup_es(cloud_id, user, pw, index, reset):
    es = Elasticsearch(cloud_id=cloud_id, basic_auth=(user, pw))
    if reset and es.indices.exists(index=index):
        es.indices.delete(index=index)

    if not es.indices.exists(index=index):
        mapping = {
            "properties": {
                "date": {"type": "date"},
                "report_id": {"type": "keyword"},
                "source": {"type": "keyword"},
                "target": {"type": "keyword"},
                "coordinates": {"type": "geo_point"},
                "summary": {"type": "text"},
                "details": {"type": "text"}
            }
        }
        es.indices.create(index=index, mappings=mapping)

    return es


def bulk_ingest(es, index, docs):
    try:
        for ok, action in streaming_bulk(client=es, index=index, actions=yield_doc(docs)):
            if not ok:
                logging.error(f"{ok} {action}")
    except BulkIndexError as e:
        print(f"{len(e.errors)} document(s) failed to index.")
        for error in e.errors:
            print(error)



def yield_doc(docs):
    for doc in docs:
        # print(json.dumps(doc))
        yield json.dumps(doc)


def random_date(start_date, end_date):
    delta = end_date - start_date
    random_days = random.randint(0, delta.days)
    return start_date + timedelta(days=random_days)


def generate_summary(details):
    sentences = details.split(". ")
    if len(sentences) > 1:
        summary = sentences[0] + "."
    else:
        summary = details
    return summary


start_date = datetime(2024, 1, 1)
end_date = datetime(2024, 4, 3)

countries = {
    "Afghanistan": [67.7100, 33.9391],
    "Algeria": [1.6596, 28.0339],
    "Argentina": [-63.6167, -38.4161],
    "Australia": [133.7751, -25.2744],
    "Azerbaijan": [47.5769, 40.1431],
    "Bahrain": [50.5577, 26.0667],
    "Bangladesh": [90.3563, 23.6850],
    "Belarus": [27.9534, 53.7098],
    "Brazil": [-51.9253, -14.2350],
    "Cameroon": [12.3547, 7.3697],
    "Canada": [-106.3468, 56.1304],
    "China": [104.1954, 35.8617],
    "Colombia": [-74.2973, 4.5709],
    "Cuba": [-77.7812, 21.5218],
    "Democratic Republic of the Congo": [21.7587, -4.0383],
    "Egypt": [30.8025, 26.8206],
    "Ethiopia": [40.4897, 9.1450],
    "Germany": [10.4515, 51.1657],
    "India": [78.9629, 20.5937],
    "Indonesia": [113.9213, -0.7893],
    "Iran": [53.6880, 32.4279],
    "Iraq": [43.6793, 33.2232],
    "Israel": [34.8516, 31.0461],
    "Italy": [12.5674, 41.8719],
    "Japan": [138.2529, 36.2048],
    "Jordan": [36.2384, 30.5852],
    "Kazakhstan": [66.9237, 48.0196],
    "Kenya": [37.9062, -0.0236],
    "Lebanon": [35.8623, 33.8547],
    "Libya": [17.2283, 26.3351],
    "Malaysia": [101.9758, 4.2105],
    "Mexico": [-102.5528, 23.6345],
    "Nigeria": [8.6753, 9.0820],
    "North Korea": [127.7669, 35.9078],
    "Pakistan": [69.3451, 30.3753],
    "Philippines": [121.7740, 12.8797],
    "Russia": [105.3188, 61.5240],
    "Saudi Arabia": [45.0792, 23.8859],
    "Somalia": [46.1996, 5.1521],
    "South Korea": [127.7669, 35.9078],
    "South Sudan": [31.3070, 6.8770],
    "Sudan": [30.2176, 12.8628],
    "Syria": [38.9968, 34.8021],
    "Taiwan": [120.9605, 23.6978],
    "Turkey": [35.2433, 38.9637],
    "Ukraine": [31.1656, 48.3794],
    "United Arab Emirates": [53.8478, 23.4241],
    "United Kingdom": [-3.4360, 55.3781],
    "Yemen": [48.5164, 15.5527]
}



groups = [
    "ISIS",
    "Al-Qaeda",
    "Taliban",
    "Hamas",
    "Hezbollah",
    "Boko Haram",
    "FARC",
    "Al-Shabaab",
    "Lashkar-e-Taiba",
    "PKK",
    "Abu Sayyaf",
    "Ansar al-Sharia",
    "Houthi rebels",
    "Jaish-e-Mohammed",
    "Jemaah Islamiyah"
]
sources = [
    "Confidential informant",
    "Satellite imagery",
    "Electronic intercepts",
    "Human intelligence source",
    "Open-source intelligence",
    "Field operatives",
    "Technical surveillance",
    "Cryptography analysis",
    "Social media monitoring",
    "Cyber forensics",
    "Interrogation",
    "Undercover agents",
    "Defector debriefing",
    "Measurement and signals intelligence",
    "Radar intelligence",
]

details_options = [
    "According to a reliable source, suspicious activity has been detected near the border of {0}. This activity includes the movement of unidentified vehicles and individuals. Security forces are closely monitoring the situation and have increased patrols in the area. Additionally, drones have been deployed for aerial surveillance to gather more information. The source suggests that this may be indicative of a potential incursion.",
    "Electronic intercepts indicate heightened chatter among members of {0}. Analysis suggests they are discussing potential targets and coordination for an upcoming operation. Intelligence agencies are actively monitoring communications channels to intercept any further details. Additionally, cyber forensics teams are working to trace the origin of the communications. The intercepted messages hint at a significant attack being planned.",
    "{0} has acquired advanced weapons technology. Recent intelligence suggests they may be testing these weapons in undisclosed locations. Satellite imagery analysis has revealed construction activity consistent with weapons testing facilities. Intelligence agencies are working to pinpoint the exact locations of these facilities for further investigation. The acquisition of advanced weaponry raises concerns about regional stability.",
    "Satellite imagery reveals movement of troops in the vicinity of {0}. Additional reconnaissance efforts are underway to gather more information. Surveillance drones have been deployed to monitor troop movements and identify any potential threats. Analysis of the satellite images suggests a buildup of military forces along the border. This has raised tensions in the region and sparked concerns of a possible conflict.",
    "{0} is suspected to be planning a large-scale cyber attack. Preliminary analysis indicates they have already compromised several critical systems. Cybersecurity experts are working to contain the breach and strengthen defenses. Meanwhile, intelligence agencies are investigating the motives behind the cyber attack and attempting to identify the perpetrators. The potential impact of the attack on national security is being assessed.",
    "Recent intelligence suggests that {0} is planning to assassinate a high-profile political figure. Security measures have been heightened in response to this threat. Close protection teams have been deployed to safeguard the target and prevent any potential attacks. Additionally, investigations are underway to identify the individuals involved in the assassination plot. The threat level in the area has been raised to ensure the safety of key government officials.",
    "Samples collected indicate possible development of biological weapons by {0}. Analysis of these samples is ongoing to confirm the nature of the threat. Specialized laboratories are conducting tests to identify the specific pathogens and toxins. Additionally, biosecurity measures have been enhanced to prevent the spread of any potential biohazards. The development of biological weapons poses a grave threat to regional stability and global security.",
    "A sophisticated network for financing terrorist activities has been traced back to {0}. Efforts to disrupt this network are currently underway. Financial intelligence units are tracking suspicious transactions and freezing assets linked to terrorist financing. Additionally, diplomatic efforts are being made to gain international cooperation in dismantling the terrorist financing network. The disruption of terrorist financing is crucial in weakening terrorist organizations and preventing future attacks.",
    "An insider report reveals plans for sabotage by operatives linked to {0}. Security agencies have been alerted to prevent any potential attacks. Counterterrorism units are conducting raids to apprehend the suspects involved in the sabotage plot. Additionally, critical infrastructure sites are being secured to prevent unauthorized access. The sabotage plot poses a significant threat to national security and public safety.",
    "Unusual behavior by individuals with ties to {0} has raised suspicions of espionage. Surveillance efforts have been increased to monitor their activities. Intelligence operatives are conducting covert surveillance operations to gather evidence of espionage activities. Additionally, counterintelligence measures are being implemented to safeguard classified information. The infiltration of foreign agents poses a serious threat to national security.",
    "According to recent intelligence, {0} is planning a series of coordinated attacks in major cities. The group has mobilized its operatives and acquired weapons and explosives. Intelligence agencies are working to disrupt the plot and prevent the attacks. Increased security measures have been implemented in potential target areas. The coordinated attacks pose a significant threat to public safety and national security.",
    "{0} has been conducting cyber espionage operations targeting government agencies and critical infrastructure. Cybersecurity experts have detected malware and hacking attempts originating from {0} servers. Countermeasures are being implemented to defend against cyber attacks and secure sensitive data. Additionally, diplomatic efforts are underway to address the issue and prevent further cyber intrusions. The cyber espionage activities pose a serious threat to national security and economic stability.",
    "Recent intelligence suggests that {0} is stockpiling chemical weapons. Surveillance satellites have detected suspicious activity at undisclosed facilities. Analysis of satellite imagery indicates the presence of chemical storage containers. International efforts are underway to investigate the allegations and ensure compliance with chemical weapons treaties. The proliferation of chemical weapons poses a grave threat to regional security and stability.",
    "A covert operation conducted by {0} has been uncovered by intelligence agencies. Surveillance teams have observed suspicious activity at clandestine meeting locations. Informants have provided valuable information about the operation's objectives and participants. Counterintelligence measures are being implemented to disrupt the operation and apprehend the operatives involved. The covert operation poses a significant threat to national security and diplomatic relations.",
    "Tensions between {0} and neighboring countries have escalated due to territorial disputes. Military forces have been mobilized along the border, increasing the risk of conflict. Diplomatic efforts to resolve the disputes peacefully have been unsuccessful. Intelligence agencies are closely monitoring the situation for any signs of military aggression. The territorial disputes pose a serious threat to regional stability and security.",
    "Intelligence indicates that {0} is providing support to terrorist organizations operating in the region. Financial transactions and logistical support have been traced back to {0}. Diplomatic pressure is being applied to {0} to cease its support for terrorism. Additionally, international cooperation is being sought to disrupt the flow of funds and weapons to terrorist groups. The support provided by {0} enables terrorist activities and undermines efforts to combat terrorism.",
    "Recent cyber attacks targeting critical infrastructure in {0} have been traced back to state-sponsored hackers. Evidence suggests the involvement of {0} in orchestrating the attacks. Diplomatic channels are being used to address the cyber threats and hold {0} accountable for its actions. Cybersecurity measures are being enhanced to defend against future attacks and mitigate potential damage. The cyber attacks pose a significant threat to national security and economic stability.",
    "{0} is suspected of conducting covert operations to undermine stability in the region. Intelligence agencies have uncovered evidence of {0} involvement in sponsoring insurgent groups. Diplomatic efforts are being made to address the issue and prevent further destabilization. Security forces are on high alert to counter any attempts to incite violence. The covert operations pose a serious threat to regional security and peace.",
    "According to intelligence reports, {0} is developing ballistic missile capabilities. Satellite imagery has revealed construction activity at missile testing sites. Analysis suggests the development of long-range missiles capable of reaching neighboring countries. International efforts are being made to address the proliferation of ballistic missile technology. The development of ballistic missiles by {0} poses a significant threat to regional security and stability.",
    "Intelligence indicates that {0} is planning to conduct cyber attacks against critical infrastructure. Cybersecurity experts have detected malware and hacking attempts originating from {0}. Countermeasures are being implemented to defend against cyber attacks and safeguard sensitive data.",
]

# drug stuff
details_options.extend([
    "Recent intelligence suggests that {0} is a major hub for drug trafficking operations. Surveillance efforts have detected increased movement of narcotics through {0}'s ports and airports. Intelligence agencies suspect the involvement of powerful cartels in orchestrating the drug trade. Law enforcement agencies are working to dismantle the trafficking networks and disrupt the flow of illegal drugs. The drug trafficking activities pose a significant threat to public health and national security.",
    "Undercover operations have uncovered a drug smuggling ring operating in {0}. Informants have provided valuable information about the trafficking routes and distribution networks. Law enforcement agencies are conducting raids to seize contraband and apprehend the smugglers. Additionally, efforts are being made to strengthen border security to prevent the entry of illegal drugs. The drug smuggling ring poses a serious threat to community safety and public order in {0}.",
    "Intelligence reports indicate that {0} is a transit point for drug shipments destined for international markets. Surveillance operations have identified warehouses and clandestine facilities used for storing narcotics. Law enforcement agencies are working with international partners to intercept drug shipments and apprehend traffickers. Additionally, efforts are underway to disrupt the financial networks supporting the drug trade. The transit of illegal drugs through {0} poses a significant challenge to regional law enforcement.",
    "Recent seizures of illicit drugs have raised concerns about the extent of drug trafficking in {0}. Intelligence suggests the involvement of organized crime groups in smuggling narcotics. Law enforcement agencies are conducting investigations to identify the sources of the drugs and dismantle the trafficking networks. Additionally, efforts are being made to increase cooperation with neighboring countries to address cross-border drug trafficking. The illicit drug trade poses a serious threat to public health and security in {0}.",
    "Surveillance operations have identified clandestine drug laboratories operating in {0}. Intelligence suggests that these laboratories are involved in the production of methamphetamine and other illicit substances. Law enforcement agencies are conducting raids to shut down the laboratories and apprehend the operators. Additionally, efforts are underway to track the distribution networks supplying precursor chemicals. The presence of drug laboratories poses a significant risk to public safety and environmental health in {0}.",
    "Intelligence reports suggest that {0} is a major producer of opium and cannabis. Satellite imagery has revealed extensive cultivation of poppy fields and marijuana plantations in remote areas. Law enforcement agencies are working to eradicate the illicit crops and disrupt the drug production cycle. Additionally, efforts are being made to provide alternative livelihoods for farmers involved in drug cultivation. The production of opium and cannabis in {0} fuels the global drug trade and contributes to drug-related crime and instability.",
    "Recent interceptions of drug shipments have exposed the involvement of corrupt officials in {0}. Intelligence suggests that law enforcement agencies are compromised by drug traffickers, allowing narcotics to pass through checkpoints unchecked. Efforts are underway to root out corruption within law enforcement agencies and strengthen internal controls. Additionally, measures are being implemented to enhance transparency and accountability in government institutions. The infiltration of drug cartels into {0}'s law enforcement poses a serious threat to the rule of law and undermines efforts to combat drug trafficking.",
    "Intelligence reports indicate that {0} is a primary source of precursor chemicals used in the production of synthetic drugs. Surveillance efforts have identified chemical factories supplying illicit drug manufacturers. Law enforcement agencies are working to disrupt the supply chain of precursor chemicals and prevent their diversion for illegal purposes. Additionally, international cooperation is being sought to regulate the trade of precursor chemicals and prevent their misuse. The trafficking of precursor chemicals from {0} facilitates the production of synthetic drugs and fuels the global narcotics trade.",
    "Undercover operations have uncovered drug trafficking routes linking {0} to neighboring countries. Intelligence suggests that cross-border smuggling networks are transporting narcotics through land and maritime routes. Law enforcement agencies are collaborating with international partners to intercept drug shipments and dismantle trafficking networks. Additionally, efforts are being made to enhance border security and strengthen customs controls. The cross-border trafficking of drugs poses a significant challenge to regional law enforcement and border security in {0}.",
    "Recent intelligence indicates that {0} is a destination for drug trafficking organizations seeking to launder illicit proceeds. Financial investigations have uncovered money laundering operations involving front companies and shell corporations. Law enforcement agencies are working to identify and seize assets acquired through drug trafficking activities. Additionally, measures are being implemented to enhance anti-money laundering regulations and strengthen financial oversight. The laundering of illicit proceeds in {0} enables drug traffickers to conceal their criminal activities and legitimize their profits."
])

# human trafficking stuff
details_options.extend([
    "Recent intelligence suggests that {0} is a hotspot for human trafficking operations. Investigations have uncovered trafficking networks exploiting vulnerable individuals for forced labor and sexual exploitation. Law enforcement agencies are conducting raids on brothels and sweatshops where victims are held captive. Additionally, efforts are being made to raise awareness and provide support services for victims of human trafficking. The human trafficking networks operating in {0} pose a grave threat to human rights and dignity.",
    "Undercover operations have revealed a human trafficking ring operating in {0}. Informants have provided crucial information about the recruitment and exploitation of victims. Law enforcement agencies are working to dismantle the trafficking network and rescue the victims. Additionally, efforts are underway to prosecute the perpetrators and provide rehabilitation services for survivors. The human trafficking ring in {0} preys on vulnerable individuals and exploits them for profit.",
    "Intelligence reports indicate that {0} is a transit point for human trafficking routes. Surveillance efforts have identified smuggling networks transporting victims across borders. Law enforcement agencies are collaborating with international partners to intercept trafficking routes and rescue victims. Additionally, efforts are being made to strengthen border controls and enhance cooperation with neighboring countries. The trafficking of humans through {0} poses a serious threat to global efforts to combat human trafficking.",
    "Recent rescues of trafficking victims have shed light on the extent of human trafficking in {0}. Intelligence suggests that victims are lured with false promises of employment and then subjected to exploitation. Law enforcement agencies are conducting investigations to identify and apprehend traffickers. Additionally, efforts are being made to provide comprehensive support services for survivors of human trafficking. The prevalence of human trafficking in {0} underscores the need for coordinated action to address this form of modern slavery.",
    "Surveillance operations have identified clandestine brothels and massage parlors involved in human trafficking in {0}. Intelligence suggests that victims are kept in squalid conditions and subjected to physical and sexual abuse. Law enforcement agencies are conducting raids to rescue victims and apprehend traffickers. Additionally, efforts are underway to prosecute the owners of the establishments and provide assistance to survivors. The presence of human trafficking operations in {0} highlights the need for stronger laws and enforcement mechanisms to combat this heinous crime.",
    "Intelligence reports suggest that {0} is a destination for trafficked persons subjected to forced labor and sexual exploitation. Surveillance efforts have identified establishments where victims are exploited. Law enforcement agencies are conducting investigations to identify and rescue victims of human trafficking. Additionally, efforts are being made to provide comprehensive support services for survivors, including medical care and legal assistance. The trafficking of humans into {0} for exploitation is a violation of basic human rights and must be addressed with urgency.",
    "Recent interceptions of trafficking victims at {0}'s airports and border crossings have raised concerns about the extent of human trafficking networks. Intelligence suggests that traffickers use sophisticated methods to smuggle victims across borders. Law enforcement agencies are working to strengthen border controls and enhance detection methods. Additionally, efforts are underway to increase public awareness and provide training for frontline personnel. The interception of trafficking victims underscores the need for concerted action to disrupt human trafficking networks operating in {0}.",
    "Undercover operations have uncovered online trafficking networks targeting vulnerable individuals in {0}. Intelligence suggests that traffickers use social media and online platforms to lure victims into exploitation. Law enforcement agencies are conducting cyber investigations to identify and apprehend online traffickers. Additionally, efforts are being made to raise awareness about the risks of online trafficking and provide support services for victims. The online exploitation of individuals in {0} highlights the need for enhanced cybersecurity measures and collaboration between law enforcement agencies.",
    "Intelligence reports indicate that {0} is a source of trafficked persons subjected to forced labor in other countries. Surveillance efforts have identified recruitment agencies and labor brokers involved in trafficking schemes. Law enforcement agencies are collaborating with international partners to disrupt the recruitment and exploitation of victims. Additionally, efforts are being made to strengthen regulations governing overseas employment and provide support services for returning migrants. The trafficking of {0}'s citizens for forced labor abroad is a serious human rights violation that requires coordinated action at the national and international levels.",
    "Recent investigations have uncovered child trafficking rings operating in {0}. Intelligence suggests that children are trafficked for various purposes, including sexual exploitation and forced labor. Law enforcement agencies are working to dismantle the trafficking networks and rescue the children. Additionally, efforts are being made to provide comprehensive support services for trafficked children, including psychosocial support and reintegration assistance. The trafficking of children in {0} is a grave violation of their rights and must be addressed with urgency and determination."
])


intelligence_reports = []

for i in range(NUM_REPORTS):
    report_id = f"INT-2024-{i+1:03d}"
    date = random_date(start_date, end_date).strftime("%Y-%m-%d")
    source = random.choice(sources)
    target = random.choice(list(countries.keys()) + groups)

    if target in countries:
        coordinates = countries[target]
    else:
        coordinates = None

    details = random.choice(details_options).format(target)
    summary = generate_summary(details)

    report = {
        "report_id": report_id,
        "date": date,
        "source": source,
        "target": target,
        "coordinates": coordinates,
        "summary": summary,
        "details": details,
    }
    if report["coordinates"] is None:
        report.pop("coordinates")
    intelligence_reports.append(report)

# json_data = json.dumps(intelligence_reports, indent=2)
# print(json_data)

es = setup_es(CLOUD_ID, USER, PASSWORD, INDEX, True)
bulk_ingest(es, INDEX, intelligence_reports)