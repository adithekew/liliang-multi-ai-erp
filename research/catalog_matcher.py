"""Conservative, explainable supplier-catalog retrieval.

This is NOT a neural encoder or an expert-validated trained model. It is a
precision-oriented lexical BM25 baseline with deterministic constraints to
prevent flavor substitutions and accidental non-food recommendations.
"""
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
from math import log

ALIASES={
 "stoberi":"strawberry","stroberi":"strawberry","strawberi":"strawberry",
 "strowbery":"strawberry","strawbery":"strawberry","stroberry":"strawberry",
 "strawberri":"strawberry","mangga":"mango","coklat":"chocolate",
 "cokelat":"chocolate","vanila":"vanilla","vanili":"vanilla",
 "kelapa":"coconut","durian":"durian","leci":"lychee","litchi":"lychee",
 "lecih":"lychee","nanas":"pineapple","pisang":"banana","alpukat":"avocado",
 "anggur":"grape","apel":"apple","melon":"melon","semangka":"watermelon",
 "kopi":"coffee","teh":"tea","matcha":"matcha","pandan":"pandan",
 "karamel":"caramel","kacang":"peanut","jahe":"ginger","markisa":"passionfruit",
 "sirsak":"soursop","jambu":"guava","mint":"mint","peppermint":"mint",
 "milk":"milk","susu":"milk","yoghurt":"yogurt",
 "bubuk":"powder","serbuk":"powder","powders":"powder",
 "cair":"liquid","cairan":"liquid",
 "roti":"bakery","kue":"bakery","cake":"bakery","cakes":"bakery",
 "minuman":"beverage","drink":"beverage","drinks":"beverage",
 "jelly":"confectionery","permen":"confectionery","candy":"confectionery",
 "gurih":"savory","makanan":"food",
 "rasa":"flavor","perisa":"flavor","flavour":"flavor",
 "untuk":"for","butuh":"need","membutuhkan":"need",
 "produksi":"production","bentuk":"form","dalam":"in","yang":"which",
 "dengan":"with","pada":"in","produk":"product","sedang":"currently",
}
PHRASES={"green tea":"greentea","black currant":"blackcurrant",
 "passion fruit":"passionfruit","dragon fruit":"dragonfruit",
 "jeruk nipis":"lime","jeruk lemon":"lemon",
 "white chocolate":"whitechocolate"}
FLAVORS={
 "strawberry","lemon","lime","orange","mango","chocolate","whitechocolate",
 "vanilla","coconut","durian","lychee","pineapple","banana","avocado",
 "grape","apple","melon","watermelon","coffee","tea","greentea","matcha",
 "pandan","caramel","peanut","ginger","passionfruit","soursop",
 "guava","mint","blueberry","raspberry","blackcurrant","blackberry",
 "cherry","peach","apricot","milk","butter","cheese","yogurt","almond",
 "hazelnut","pistachio","taro","tiramisu","mocha","kiwi","papaya",
 "tamarind","jackfruit","honey","vanillin","cream","custard","cinnamon",
 "apple","chicken","beef","fish","shrimp","garlic","onion","wasabi",
 "lemongrass","basil","cucumber","tomato","tuna","seafood",
}
APPLICATIONS={"bakery","beverage","dairy","confectionery","snack","savory","vape"}
APP_ALIASES={"milk":"dairy","yogurt":"dairy","dairy":"dairy",
             "bakery":"bakery","beverage":"beverage","confectionery":"confectionery",
             "snack":"snack","savory":"savory","e-cigarettes":"vape"}
FORMS={"powder","liquid","paste","emulsion","oil"}
STOPWORDS={"flavor","flavours","flavour","need","for","form","in","which",
 "with","currently","production","product","food","artificial","natural",
 "type","applications","application","text","catalog","percentage","of",
 "the","a","and","is","want","looking","requested","flavouring",
 "rasa","mixture","bahan","ingredient","bahanbaku","aku","kami","customer",
 "butuh","manufacture","technical","company","packing","sku","halal","sertifikat",
 "dokumen","document","jika","dipakai","perlu","mohon","dapat","please"}

def normalized_tokens(value):
    text=unicodedata.normalize("NFKC",str(value or "")).casefold()
    text=re.sub(r"[^a-z0-9]+"," ",text)
    for phrase,tag in sorted(PHRASES.items(),key=lambda x:-len(x[0])):
        text=re.sub(r"\b"+re.escape(phrase)+r"\b",tag,text)
    tokens=text.split()
    result=[]
    for token in tokens:
        mapped=ALIASES.get(token,token)
        if mapped==token and len(token)>=6 and token[0:3] in ("str","blu","cho","van","pin","man","coc","lem"):
            possible=[t for t in FLAVORS if len(t)>=6 and t[:3]==token[:3]
                      and SequenceMatcher(None,token,t).ratio()>=0.83]
            if len(possible)==1:mapped=possible[0]
        result.append(mapped)
    return result

def query_intent(query):
    ts=normalized_tokens(query)
    flavor={t for t in ts if t in FLAVORS}
    apps={t for t in ts if t in APPLICATIONS}
    # Milk/yogurt accompany a second named flavor as a target matrix/application.
    if "milk" in ts or "yogurt" in ts:
        if flavor-{"milk","yogurt"}:
            flavor-={"milk","yogurt"};apps.add("dairy")
    if "bakery" in ts:apps.add("bakery")
    if "beverage" in ts:apps.add("beverage")
    forms={t for t in ts if t in FORMS}
    keywords=[t for t in ts if t not in STOPWORDS and t not in APPLICATIONS
              and t not in FORMS and len(t)>2]
    return {"flavors":sorted(flavor),"applications":sorted(apps),
            "forms":sorted(forms),"keywords":sorted(set(keywords)),
            "normalized_text":" ".join(ts),"tokens":ts}

def _product_form(product):
    name=" ".join(normalized_tokens(product.get("name")))
    description=" ".join(normalized_tokens(product.get("description")))
    # Exact structured product type from supplier PDF is stored in description.
    found=re.search(r"\btype\s+(powder|liquid|paste|emulsion|oil)\b",description)
    if found:return found.group(1)
    for f in FORMS:
        if re.search(r"\b"+f+r"\b",name):return f
    return None

def _product_application(product):
    app=set(normalized_tokens(product.get("application","")))
    return app & APPLICATIONS

def _bm25_score(query_terms, document, frequencies, avgdl, total):
    terms=Counter(query_terms);tf=Counter(document);score=0.
    for term,qcount in terms.items():
        f=tf[term]
        if not f:continue
        idf=log(1+(total-frequencies[term]+0.5)/(frequencies[term]+0.5))
        score+=idf*(f*2.2)/(f+1.2*(0.25+0.75*len(document)/avgdl))*min(qcount,2)
    return score

def score_products(query, products):
    """Return Top-5 conservative lexical candidates; abstain on flavor mismatches."""
    intent=query_intent(query)
    docs=[]
    for row in products:
        p=dict(row)
        name_ts=normalized_tokens(p.get("name"))
        app_ts=normalized_tokens(p.get("application"))
        text_ts=normalized_tokens(p.get("description"))
        profile_ts=normalized_tokens(p.get("profile"))
        p_flavors=set(name_ts)&FLAVORS
        flavor_filter=set(intent["flavors"])
        if flavor_filter and not (flavor_filter&p_flavors):
            # Never recommend avocado, wasabi or fish for a strawberry inquiry.
            continue
        form=_product_form(p)
        if intent["forms"] and form and form not in intent["forms"]:
            continue
        p_app=_product_application(p)
        if intent["applications"] and p_app=={"vape"} and "vape" not in intent["applications"]:
            continue
        significant=[t for t in intent["keywords"] if t not in FLAVORS]
        # Do not return arbitrarily high-IDF products when intent is underspecified.
        if not flavor_filter and not (set(intent["keywords"]) & set(name_ts)):
            continue
        docs.append((p,name_ts,app_ts,text_ts,profile_ts,p_flavors,form,p_app))
    if not docs:return []
    # Frequency statistics are computed across all allowed candidates;
    # product names are weighted stronger than generic catalog boilerplate.
    terms=[x for x in intent["tokens"] if x not in STOPWORDS and x not in FORMS]
    if not terms:return []
    term_docs=[n*3+a+d[:35] for _,n,a,d,_,_,_,_ in docs]
    total=len(docs);freq=Counter(w for doc in term_docs for w in set(doc))
    avgdl=max(1,sum(len(doc) for doc in term_docs)/total)
    ranks=[]
    for (p,name,app,desc,profile,pflav,form,papp),doc in zip(docs,term_docs):
        title_overlap=set(intent["keywords"]) & set(name)
        lexical=_bm25_score(terms,doc,freq,avgdl,total)
        flavor_exact=bool(set(intent["flavors"])&pflav)
        app_exact=bool(set(intent["applications"])&papp)
        form_exact=bool(set(intent["forms"]) and form in intent["forms"])
        if intent["flavors"]:lexical+=12.0 if flavor_exact else 0
        lexical+=2.5*len(title_overlap)
        if form_exact:lexical+=5
        if app_exact:lexical+=3
        elif intent["applications"] and papp:lexical-=2.5
        if lexical<=0:continue
        ranks.append({"product_id":p["id"],"sku":p["sku"],"name":p["name"],
          "score":round(lexical,4),"source_ref":p.get("source_ref","UNKNOWN"),
          "unknown_attributes":["regulatory","halal_status","product_suitability"],
          "evidence_verified":False,"profile":p.get("profile"),
          "application":p.get("application"),
          "explanation":{
            "matched_terms":sorted(set(terms)&set(name+app+desc))[:12],
            "flavor_tag_match":flavor_exact,
            "application_tag_match":app_exact,
            "form_match":form_exact,
            "requested_flavors":intent["flavors"],
            "requested_forms":intent["forms"],
            "requested_applications":intent["applications"],
            "retrieval_status":"LEXICAL_CANDIDATE_UNVERIFIED",
            "limitations":"Flavor mismatch gated out; match score is not accuracy. Technical approval and datasheet evidence required."}})
    ranks.sort(key=lambda x:(-x["score"],x["sku"]))
    for idx,x in enumerate(ranks[:5],1):x["rank"]=idx
    return ranks[:5]
