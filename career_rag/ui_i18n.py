"""Small UI translation helpers for the Streamlit career app."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from career_rag.config import CONTENT_TRANSLATIONS_PATH

DEFAULT_LANGUAGE = "en"
LANGUAGE_SESSION_KEY = "ui_language"
LANGUAGE_BUTTON_LABELS = {
    "en": "ENG",
    "tr": "TUR",
}


TEXT: dict[str, dict[str, str]] = {
    "en": {
        "language.label": "Language",
        "app.title": "AI Aware Career Guide",
        "app.caption": (
            "A personalized career guidance tool that uses O*NET job data, open-ended "
            "follow-up questions [1] [2], and AI exposure data mainly from Anthropic [3] "
            "and NBER [4] to recommend careers with context about automation and future impact."
        ),
        "app.method_references": "Method references",
        "initial.instructions": (
            "Check the box by the activities you would like to do. Do not think about "
            "how much education/training is needed or how much money you will make."
        ),
        "initial.activities_header": "60 Work Activities",
        "initial.job_zone_header": "Job Zone Questions",
        "initial.current_job_zone_heading": "A. Current Job Zone",
        "initial.current_job_zone_question": (
            "What level of education, training, and experience do you currently have?"
        ),
        "initial.future_job_zone_heading": "B. Future Job Zone",
        "initial.future_job_zone_question": (
            "What level of education, training, and experience are you willing to work toward?"
        ),
        "initial.submit": "Submit",
        "followup.header": "Follow-Up Refinement",
        "followup.ambiguity_info": (
            "Your profile has some close or tied interest areas. You can answer a few "
            "follow-up questions to refine your result."
        ),
        "followup.clear_info": (
            "Your scores are clear, but you can answer a few questions to personalize "
            "the recommendations further."
        ),
        "followup.continue": "Continue with follow-up questions",
        "followup.skip": "Skip follow-up and use initial result",
        "followup.question_progress": "Question {current} of max {maximum}",
        "followup.answer_label": "Your answer",
        "followup.submit_answer": "Submit answer",
        "followup.empty_answer_warning": "Please add a short answer before continuing.",
        "followup.invalid_json_warning": (
            "The LLM response was not valid JSON after repair. A conservative fallback was saved."
        ),
        "followup.rag_error_prefix": "Could not compute follow-up RAG refinement: ",
        "final.header": "Final Career Report",
        "final.description": (
            "Generate a source-grounded report from the saved Interest Profiler profile, "
            "local O*NET data, and available AI-impact evidence."
        ),
        "final.finish_followup_info": (
            "Finish the follow-up questions to compute the refined ranking before generating the final report."
        ),
        "final.generate_button": "Generate Final Career Report",
        "final.spinner": "Retrieving O*NET and AI-impact evidence...",
        "final.validation_failed_prefix": "Final report validation failed: ",
        "final.generation_error_prefix": "Could not generate the final career report: ",
        "final.success": "Final career report generated.",
        "final.stale_warning_prefix": (
            "Hidden stale final report because it does not match the current profile: "
        ),
        "artifacts.missing_title": "RAG artifacts missing. Please run the setup/build command.",
        "artifacts.missing_list": "Missing or unusable artifacts:",
        "artifacts.rebuild": "Rebuild artifacts from raw/local sources:",
        "artifacts.verify": "Then verify:",
        "report.no_final": "No final career report is available yet.",
        "report.tab.summary": "Summary",
        "report.tab.top_matches": "Top Matches",
        "report.tab.alternatives": "Alternatives",
        "report.tab.sources": "Sources",
        "report.summary.header": "Profile Summary",
        "report.summary.top_interests": "Top interests",
        "report.summary.final_code": "Final code",
        "report.summary.current_zone": "Current zone",
        "report.summary.future_zone": "Future zone",
        "report.summary.preferences": "Preferences Used For Matching",
        "report.top_matches.header": "Top Career Matches",
        "report.top_matches.caption": (
            "This report shows up to five careers for your current Job Zone and up to five "
            "careers for the future Job Zone you are willing to work toward."
        ),
        "report.top_matches.fit": "Fit",
        "report.top_matches.detail_card": "Job detail card",
        "report.job.what_does": "What This Job Does",
        "report.job.no_description": "No local O*NET description was retrieved.",
        "report.job.main_tasks": "Main Tasks",
        "report.job.key_skills": "Key Skills",
        "report.job.education_zone": "Education / Job Zone",
        "report.job.ai_impact": "AI Impact Breakdown",
        "report.job.day_life": "Day In The Life",
        "report.ai.table.task": "Task",
        "report.ai.table.signal": "Anthropic task coverage",
        "report.ai.table.score": "Coverage value",
        "report.ai.table.source": "Source",
        "report.ai.caption": (
            "Task coverage comes from Anthropic's labor-market impacts data (Claude usage in "
            "August and November 2025). A task counts as covered when it had enough work-related "
            "Claude usage and is a task language models can do. The value is 0 when the task is "
            "not covered, 0.5 when it is covered through augmentation-style use (people work with "
            "Claude), and 1 when it is covered through automation-style use (Claude does the task); "
            "values in between are a mix. Covered does not mean the job will disappear. "
            "Not covered does not mean the task is safe from AI either: it only means this Claude data "
            "did not show it, and it says nothing about other AI tools, robots or future models. "
            "No data means Anthropic has no row for this exact O*NET task, which is not the same as 0."
        ),
        "report.ai.no_rows": "No AI impact rows were available for this occupation.",
        "report.usage.title": "How people use Claude for this work ({month})",
        "report.usage.share": "{global_pct} of all Claude.ai conversations worldwide were about this occupation's tasks.",
        "report.usage.share_turkey": "In Turkey: {turkey_pct}.",
        "report.usage.share_turkey_missing": "Turkey: not published (fewer conversations than Anthropic's threshold).",
        "report.usage.share_note": "This shows how much people use Claude for this work, not how many jobs change.",
        "report.usage.split": (
            "{automation_pct} automation-style (Claude carries out the task), "
            "{augmentation_pct} augmentation-style (the person works through it with Claude)."
        ),
        "report.usage.time": (
            "Anthropic's estimate: about {hours} hours for a person alone, about {minutes} minutes with AI. "
            "These are model estimates from conversations, not measured productivity."
        ),
        "report.usage.below": "under {value}",
        "report.ilo.title": "How exposed this kind of work is to generative AI (ILO)",
        "report.ilo.score": "Average task score {mean} on a 0-1 scale; tasks in the group differ by about {sd}.",
        "report.ilo.scope": (
            "This is the ILO's score for the broader ISCO-08 group {code} \"{title}\", which also covers "
            "{others} other careers in this app."
        ),
        "report.ilo.scope_single": "This is the ILO's score for the ISCO-08 group {code} \"{title}\".",
        "report.ilo.meaning": (
            "Experts and a model judged each task's potential exposure: an assessment, not observed use, "
            "so it can differ from the Claude data above."
        ),
        "report.ilo.none": "The ILO publishes no score for this career's occupation group.",
        "source.ilo.section": "Annex Table A1: mean, standard deviation and exposure gradient of each ISCO-08 occupation",
        "source.ilo.note": (
            "Linked to the career through its ISCO-08 group (O*NET's ESCO crosswalk, ROADMAP 6.3); "
            "the score is for the whole group."
        ),
        "report.research.title": "What research says",
        "report.research.in_source": "In the source's words",
        "report.research.pages": "p. {pages}",
        "report.research.none": "No study in our collection is specific to this career yet.",
        "report.research.caption": (
            "Claims from the reports and papers on AI and work in our collection, matched to this career by similarity "
            "and checked for relevance by an AI model; in our test about 7 in 10 shown claims were relevant. "
            "Quotes are verbatim from the source."
        ),
        # Sentences the report builder writes (ROADMAP 6.1d); the English ones are the original wording.
        "report.why.technology": (
            "You said you prefer technology, and this path keeps the work close to technical systems and tools. {marker}"
        ),
        "report.why.analytical": "The role uses analytical thinking, data, math, or structured problem solving.",
        "report.why.fast_paced": "It can support fast-paced project work where you solve several smaller problems over time.",
        "report.why.own_thing": (
            "The skill set can transfer into independent consulting, product ideas, or building your own project."
        ),
        "report.why.lower_social": (
            "It can involve less continuous people-facing interaction than many Social-heavy career paths."
        ),
        "report.why.default": (
            "These roles are included using the submitted Interest Profiler result ({interests}) and selected "
            "Job Zones, including future Job Zone {zone}. {marker}"
        ),
        "report.guidance.default": (
            "Use future job zone for aspirational recommendations, current job zone for immediate options."
        ),
        # The follow-up agent's note (ip_followup_agent.py), word for word.
        "report.guidance.followup": (
            "Use the original O*NET Interest Profiler matches as the candidate pool, "
            "then rank them by the open-ended filtering answers and O*NET occupation signals."
        ),
        "report.resolution_note": "Displayed as {display_title}; O*NET evidence retrieved from {resolved_title}.",
        "new_titles.header": "A new job title?",
        "new_titles.caption": (
            "Titles like prompt engineer have no O\\*NET occupation of their own. "
            "Pick one to see its closest O\\*NET roles and their AI evidence."
        ),
        "new_titles.select": "Job title",
        "new_titles.placeholder": "Choose or type a title",
        "new_titles.note": (
            "O\\*NET has no occupation equivalent to {title}, so we can only show its closest O\\*NET occupations below. "
            "They are not the same job, and their AI evidence is an approximation."
        ),
        "new_titles.source.onet": "These are the occupations O\\*NET lists this title under.",
        "new_titles.source.adjusted": (
            "O\\*NET lists this title under some occupations; those that don't fit the usual job were left out or replaced."
        ),
        "new_titles.source.proposed": "O\\*NET doesn't list this title at all; these closest occupations were chosen by hand and reviewed.",
        # The card test and profile screens (moved from interest_profiler_app.py, ROADMAP 7.1).
        "hero.eyebrow": "AI career guide",
        "hero.status": "Interest profile",
        "assessment.header": "Start with quick swipes",
        "assessment.caption": "Answer each work activity with a simple yes or no.",
        "assessment.activity_prompt": "Would you enjoy this activity?",
        "assessment.progress": "Question {current} of {total}",
        "assessment.previous_yes": "Previous answer: Yes",
        "assessment.previous_no": "Previous answer: No",
        "assessment.no": "No",
        "assessment.yes": "Yes",
        "assessment.back": "Back",
        "assessment.reset": "Reset",
        "assessment.done_title": "All activity cards answered",
        "assessment.done_text": "Choose the preparation levels to create your career matches.",
        "assessment.completed": "{answered} of {total} cards answered",
        "assessment.submit": "Build my matches",
        "assessment.spinner": "Building your matches...",
        "assessment.incomplete": "Answer every activity card before building matches.",
        "assessment.flat_profile": (
            "You gave the same answer in all six interest areas, so no careers can be matched. "
            "Please review your answers or try again another time."
        ),
        "assessment.saved": "Profile updated from your card choices.",
        "profile.ready": "Profile ready",
        "profile.code": "Career code",
        "profile.current_zone": "Current zone",
        "profile.future_zone": "Future zone",
        "followup.kicker": "Refine",
        "final.kicker": "Report",
        "report.alternative.reason": "Related career from the submitted Interest Profiler matches.",
        "report.ai_summary.resolved": " O*NET/AI evidence is retrieved from {resolved_title}.",
        "report.ai_summary.exposure": (
            "The strongest local Anthropic occupation signal reports observed exposure of {value} for the resolved "
            "O*NET occupation {marker}."
        ),
        "report.ai_summary.task_rows": (
            "Local Anthropic task rows were found by exact O*NET task ID for the resolved occupation {marker}."
        ),
        "report.ai_summary.no_rows": "No local Anthropic task metric was found for the displayed O*NET task rows.",
        "report.ai_summary.role": (
            "My read is that AI is more likely to become a helper around repeatable, text-heavy, or digital parts of "
            "the work than a clean replacement for the whole occupation. The human side still matters most where the "
            "job depends on judgment, context, quality checking, accountability, and knowing what a good result "
            "should look like."
        ),
        "report.ai_summary.context": (
            "Broader GenAI adoption evidence is used as labor-market context, not as task-level scoring {marker}."
        ),
        "report.day.no_tasks": (
            "The day-to-day rhythm is hard to pin down from the retrieved rows, so this career deserves more "
            "occupation-specific research before deciding."
        ),
        "source.ip.title": "O*NET Interest Profiler Short Form and its career-matching rule",
        "source.ip.section": (
            "RIASEC scores, Holland code, Job Zone choices; matching careers by O*NET's rule "
            "(interest-profile correlation, Best/Great/Good fit)"
        ),
        "source.ip.note": "Short form: {short_form}; matching rule (Gregory & Lewis 2016): {rule}",
        "source.onet.title": "O*NET occupation data - {title}",
        "source.onet.section": (
            "description, tasks, skills, knowledge, abilities, education, job zone, work context, software, "
            "related occupations"
        ),
        "source.onet.alias_section": "occupation title, O*NET-SOC alias resolution, and job zone",
        "source.onet.note": "O*NET-SOC {code}",
        "source.anthropic.title": "Anthropic Economic Index and labor-market impacts",
        "source.anthropic.section": "observed occupation/task exposure and task penetration rows",
        "source.anthropic.note": (
            "Task rows are used only when local rows match the resolved O*NET-SOC code and exact O*NET task ID."
        ),
        "source.nber.section": "broad GenAI adoption context",
        "source.nber.note": "Used as broad labor-market/adoption context, not as task-level automation scoring.",
        "source.usage.title": "Anthropic Economic Index, release 2026-06-26 (Claude.ai, per occupation)",
        "source.usage.section": "soc_occupation rows for {month}, GLOBAL and TUR",
        "source.usage.note": "A missing Turkey value means Anthropic did not publish it (below its sample threshold).",
        "source.research.note": (
            "Claims matched by embedding similarity, then checked for relevance by an LLM (CHANGELOG 032)."
        ),
        "report.alternatives.header": "Alternative Careers",
        "report.alternatives.none": "No alternatives were resolved from local O*NET evidence.",
        "report.sources.header": "Sources",
        "report.sources.expander": "View numbered citations",
        "report.no_local_evidence": "No local evidence was retrieved for this section.",
        "report.skills.software": "Software / technical tools",
        "report.skills.technical": "Technical and domain skills",
        "report.skills.foundational": "Foundational communication",
        "report.skills.knowledge": "Knowledge areas",
        "report.skills.in_demand": "In demand",
        "report.preferences.tasks": "Tasks and tools",
        "report.preferences.work_style": "Work style",
        "report.preferences.people": "People and setting",
        "report.preferences.direction": "Career direction",
        "report.preferences.other": "Other",
        "report.education.typical": "Typical preparation: ",
        "report.education.training": "Experience and training: ",
        "report.education.responses": "O*NET education responses",
        "report.education.none": "No local education or Job Zone evidence was retrieved for this section.",
        "report.job_zone.unavailable": "Job Zone unavailable",
        "report.job_zone.preparation_unavailable": "preparation level unavailable",
        "report.job_zone.title": "Job Zone {zone} ({explanation})",
        "report.job_zone.typical_education": "typical education: {education}",
        "report.job_zone.training": "training: {training}",
        "report.career_fallback": "Career",
        "report.education.master_with_bachelor": (
            "Most O*NET responses point to a master's degree for this role; "
            "bachelor's-degree paths are present but less common."
        ),
        "report.education.master": "Most O*NET responses point to a master's degree for this role.",
        "report.education.bachelor_with_master": (
            "Most O*NET responses point to a bachelor's degree; master's-level preparation is also common."
        ),
        "report.education.bachelor": "Most O*NET responses point to a bachelor's degree for this role.",
        "report.education.doctoral": (
            "Most O*NET responses point to doctoral or professional-degree preparation for this role."
        ),
        "report.education.associate": (
            "Most O*NET responses point to associate-degree or vocational preparation for this role."
        ),
        "report.education.high_school": (
            "Most O*NET responses point to high-school-level preparation for this role."
        ),
        "report.education.dynamic": "Most O*NET responses point to {label} for this role.",
        "common.na": "N/A",
    },
    "tr": {
        "language.label": "Dil",
        "app.title": "Yapay Zekâ Farkındalıklı Kariyer Rehberi",
        "app.caption": (
            "O*NET meslek verilerini, açık uçlu takip sorularını [1] [2] ve ağırlıklı olarak "
            "Anthropic [3] ile NBER [4] kaynaklı yapay zekâ etkisi verilerini kullanarak "
            "otomasyon ve gelecekteki etki bağlamıyla kariyer önerileri sunan kişiselleştirilmiş "
            "bir kariyer rehberliği aracı."
        ),
        "app.method_references": "Yöntem kaynakları",
        "initial.instructions": (
            "Yapmak isteyeceğin etkinliklerin yanındaki kutuyu işaretle. Ne kadar eğitim/"
            "hazırlık gerektiğini veya ne kadar para kazanacağını düşünme."
        ),
        "initial.activities_header": "60 İş Etkinliği",
        "initial.job_zone_header": "İş Bölgesi Soruları",
        "initial.current_job_zone_heading": "A. Mevcut İş Bölgesi",
        "initial.current_job_zone_question": (
            "Şu anda hangi eğitim, hazırlık ve deneyim düzeyine sahipsin?"
        ),
        "initial.future_job_zone_heading": "B. Hedeflenen İş Bölgesi",
        "initial.future_job_zone_question": (
            "Hangi eğitim, hazırlık ve deneyim düzeyi için çalışmaya isteklisin?"
        ),
        "initial.submit": "Gönder",
        "followup.header": "Takip Sorularıyla İyileştirme",
        "followup.ambiguity_info": (
            "Profilinde birbirine yakın veya eşit çıkan ilgi alanları var. Sonucunu iyileştirmek "
            "için birkaç takip sorusu yanıtlayabilirsin."
        ),
        "followup.clear_info": (
            "Puanların net görünüyor, ancak önerileri daha kişisel hale getirmek için birkaç "
            "soru yanıtlayabilirsin."
        ),
        "followup.continue": "Takip sorularıyla devam et",
        "followup.skip": "Takip sorularını atla ve ilk sonucu kullan",
        "followup.question_progress": "Soru {current} / en fazla {maximum}",
        "followup.answer_label": "Yanıtın",
        "followup.submit_answer": "Yanıtı gönder",
        "followup.empty_answer_warning": "Devam etmeden önce kısa bir yanıt ekle.",
        "followup.invalid_json_warning": (
            "LLM yanıtı onarımdan sonra geçerli JSON değildi. Temkinli bir yedek sonuç kaydedildi."
        ),
        "followup.rag_error_prefix": "Takip sorusu RAG iyileştirmesi hesaplanamadı: ",
        "final.header": "Nihai Kariyer Raporu",
        "final.description": (
            "Kaydedilmiş Interest Profiler profili, yerel O*NET verileri ve mevcut yapay zekâ "
            "etkisi kanıtlarından kaynaklara dayalı bir rapor üret."
        ),
        "final.finish_followup_info": (
            "Nihai raporu üretmeden önce iyileştirilmiş sıralamayı hesaplamak için takip "
            "sorularını tamamla."
        ),
        "final.generate_button": "Nihai Kariyer Raporu Oluştur",
        "final.spinner": "O*NET ve yapay zekâ etkisi kanıtları getiriliyor...",
        "final.validation_failed_prefix": "Nihai rapor doğrulaması başarısız: ",
        "final.generation_error_prefix": "Nihai kariyer raporu oluşturulamadı: ",
        "final.success": "Nihai kariyer raporu oluşturuldu.",
        "final.stale_warning_prefix": (
            "Geçerli profille eşleşmediği için eski nihai rapor gizlendi: "
        ),
        "artifacts.missing_title": "RAG dosyaları eksik. Lütfen kurulum/oluşturma komutunu çalıştır.",
        "artifacts.missing_list": "Eksik veya kullanılamayan dosyalar:",
        "artifacts.rebuild": "Ham/yerel kaynaklardan yeniden oluştur:",
        "artifacts.verify": "Ardından doğrula:",
        "report.no_final": "Henüz nihai kariyer raporu yok.",
        "report.tab.summary": "Özet",
        "report.tab.top_matches": "En Uygunlar",
        "report.tab.alternatives": "Alternatifler",
        "report.tab.sources": "Kaynaklar",
        "report.summary.header": "Profil Özeti",
        "report.summary.top_interests": "En güçlü ilgi alanları",
        "report.summary.final_code": "Nihai kod",
        "report.summary.current_zone": "Mevcut bölge",
        "report.summary.future_zone": "Hedef bölge",
        "report.summary.preferences": "Eşleştirmede Kullanılan Tercihler",
        "report.top_matches.header": "En Uygun Kariyer Eşleşmeleri",
        "report.top_matches.caption": (
            "Bu rapor, mevcut İş Bölgen için en fazla beş kariyeri ve ulaşmaya istekli olduğun "
            "gelecek İş Bölgesi için en fazla beş kariyeri gösterir."
        ),
        "report.top_matches.fit": "Uyum",
        "report.top_matches.detail_card": "İş ayrıntı kartı",
        "report.job.what_does": "Bu İş Ne Yapar",
        "report.job.no_description": "Yerel O*NET açıklaması getirilemedi.",
        "report.job.main_tasks": "Ana Görevler",
        "report.job.key_skills": "Temel Beceriler",
        "report.job.education_zone": "Eğitim / İş Bölgesi",
        "report.job.ai_impact": "Yapay Zekâ Etkisi Dağılımı",
        "report.job.day_life": "Günlük İş Akışı",
        "report.ai.table.task": "Görev",
        "report.ai.table.signal": "Anthropic görev kapsamı",
        "report.ai.table.score": "Kapsam değeri",
        "report.ai.table.source": "Kaynak",
        "report.ai.caption": (
            "Görev kapsamı, Anthropic'in işgücü piyasası etkileri verisinden gelir (Ağustos ve Kasım "
            "2025 Claude kullanımı). Bir görev, işle ilgili yeterli Claude kullanımı olduğunda ve dil "
            "modellerinin yapabileceği bir görev olduğunda kapsanmış sayılır. Değer, görev kapsanmıyorsa "
            "0, destekleme tarzı kullanımla (insanlar Claude ile birlikte çalışır) kapsanıyorsa 0,5, "
            "otomasyon tarzı kullanımla (görevi Claude yapar) kapsanıyorsa 1'dir; aradaki değerler "
            "ikisinin karışımıdır. Kapsanıyor olması mesleğin ortadan kalkacağı anlamına gelmez. "
            "Kapsanmıyor olması da görevin yapay zekâdan etkilenmeyeceği anlamına gelmez: yalnızca bu "
            "Claude verisinde görülmediğini gösterir; başka yapay zekâ araçları, robotlar veya gelecekteki "
            "modeller hakkında bir şey söylemez. "
            "Veri yok, Anthropic'in bu O*NET görevi için satırı olmadığı anlamına gelir; bu 0 ile aynı "
            "şey değildir."
        ),
        "report.ai.no_rows": "Bu meslek için yapay zekâ etkisi satırı bulunamadı.",
        "report.usage.title": "İnsanlar bu iş için Claude'u nasıl kullanıyor ({month})",
        "report.usage.share": "Dünya genelindeki tüm Claude.ai konuşmalarında bu mesleğin görevlerinin payı: {global_pct}.",
        "report.usage.share_turkey": "Türkiye'de: {turkey_pct}.",
        "report.usage.share_turkey_missing": "Türkiye: yayımlanmadı (konuşma sayısı Anthropic'in eşiğinin altında).",
        "report.usage.share_note": "Bu, insanların bu iş için Claude'u ne kadar kullandığını gösterir; kaç işin değiştiğini değil.",
        "report.usage.split": (
            "Otomasyon tarzı (görevi Claude yürütüyor): {automation_pct}; "
            "destekleme tarzı (kişi görevi Claude ile birlikte yürütüyor): {augmentation_pct}."
        ),
        "report.usage.time": (
            "Anthropic'in tahmini: bir kişi tek başına yaklaşık {hours} saat, yapay zekâ ile yaklaşık {minutes} dakika. "
            "Bunlar konuşmalardan yapılan model tahminleridir, ölçülmüş verimlilik değildir."
        ),
        "report.usage.below": "{value} altında",
        "report.ilo.title": "Bu tür işin üretken yapay zekâya maruziyeti (ILO)",
        "report.ilo.score": "0-1 ölçeğinde ortalama görev puanı {mean}; gruptaki görevler arasında yaklaşık {sd} fark var.",
        "report.ilo.scope": (
            "Bu, ILO'nun daha geniş ISCO-08 grubu {code} \"{title}\" için verdiği puandır; bu grup, bu uygulamadaki "
            "{others} başka kariyeri de kapsar."
        ),
        "report.ilo.scope_single": "Bu, ILO'nun ISCO-08 grubu {code} \"{title}\" için verdiği puandır.",
        "report.ilo.meaning": (
            "Uzmanlar ve bir model her görevin olası maruziyetini değerlendirdi: bu gözlemlenen kullanım değil bir "
            "değerlendirmedir, bu yüzden yukarıdaki Claude verisinden farklı olabilir."
        ),
        "report.ilo.none": "ILO bu kariyerin meslek grubu için bir puan yayımlamıyor.",
        "source.ilo.section": "Ek Tablo A1: her ISCO-08 mesleği için ortalama, standart sapma ve maruziyet derecesi",
        "source.ilo.note": (
            "Kariyere ISCO-08 grubu üzerinden bağlandı (O*NET'in ESCO eşleştirmesi, ROADMAP 6.3); puan grubun tamamı içindir."
        ),
        "report.research.title": "Araştırmalar ne diyor",
        "report.research.in_source": "Kaynaktaki ifade",
        "report.research.pages": "s. {pages}",
        "report.research.none": "Koleksiyonumuzda henüz bu mesleğe özgü bir çalışma yok.",
        "report.research.caption": (
            "Koleksiyonumuzdaki yapay zekâ ve iş konulu rapor ve makalelerden alınan bulgular; bu mesleğe benzerlikle "
            "eşleştirildi ve bir yapay zekâ modeliyle ilgililik açısından kontrol edildi. Testimizde gösterilen "
            "bulguların yaklaşık 10'da 7'si ilgiliydi. Alıntılar kaynaktan aynen alınmıştır (İngilizce)."
        ),
        "report.why.technology": (
            "Teknolojiyi tercih ettiğini söyledin; bu yol, işi teknik sistemlere ve araçlara yakın tutar. {marker}"
        ),
        "report.why.analytical": "Bu meslek analitik düşünme, veri, matematik veya yapılandırılmış problem çözme içerir.",
        "report.why.fast_paced": (
            "Zaman içinde birkaç küçük problemi çözdüğün, hızlı tempolu proje işlerine uygun olabilir."
        ),
        "report.why.own_thing": (
            "Bu beceriler bağımsız danışmanlığa, ürün fikirlerine veya kendi projeni kurmaya aktarılabilir."
        ),
        "report.why.lower_social": (
            "Sosyal ağırlıklı birçok kariyer yoluna göre insanlarla daha az sürekli yüz yüze çalışma gerektirebilir."
        ),
        "report.why.default": (
            "Bu meslekler, gönderdiğin Interest Profiler sonucuna ({interests}) ve seçtiğin İş Bölgelerine göre "
            "listelendi; gelecek İş Bölgesi {zone} de dahil. {marker}"
        ),
        "report.guidance.default": (
            "Hedeflediğin öneriler için gelecek İş Bölgesine, hemen başlayabileceğin seçenekler için mevcut İş "
            "Bölgene bak."
        ),
        "report.guidance.followup": (
            "Adaylar, O*NET Interest Profiler'ın ilk eşleşmeleridir; takip sorularına verdiğin yanıtlara ve "
            "O*NET meslek bilgilerine göre yeniden sıralandılar."
        ),
        "report.resolution_note": "{display_title} olarak gösteriliyor; O*NET verisi {resolved_title} mesleğinden alındı.",
        "new_titles.header": "Yeni bir meslek unvanı mı?",
        "new_titles.caption": (
            "Prompt mühendisi gibi unvanların O\\*NET'te kendi mesleği yok. "
            "Birini seç; ona en yakın O\\*NET rollerini ve onların yapay zekâ verilerini gör."
        ),
        "new_titles.select": "Meslek unvanı",
        "new_titles.placeholder": "Bir unvan seç ya da yaz",
        "new_titles.note": (
            "O\\*NET'te {title} unvanına karşılık gelen bir meslek yok; bu yüzden yalnızca ona en yakın O\\*NET "
            "mesleklerini gösterebiliyoruz. Bunlar aynı iş değil ve yapay zekâ verileri yaklaşık bir fikir verir."
        ),
        "new_titles.source.onet": "Bunlar, O\\*NET'in bu unvanı altında listelediği meslekler.",
        "new_titles.source.adjusted": (
            "O\\*NET bu unvanı bazı mesleklerin altında listeliyor; olağan işe uymayanlar çıkarıldı ya da değiştirildi."
        ),
        "new_titles.source.proposed": "O\\*NET bu unvanı hiç listelemiyor; bu en yakın meslekler elle seçildi ve gözden geçirildi.",
        # The card test and profile screens (moved from interest_profiler_app.py, ROADMAP 7.1).
        "hero.eyebrow": "YZ kariyer rehberi",
        "hero.status": "İlgi profili",
        "assessment.header": "Hızlı kartlarla başla",
        "assessment.caption": "Her iş etkinliğini yalnızca evet ya da hayır ile yanıtla.",
        "assessment.activity_prompt": "Bu etkinliği yapmak ister miydin?",
        "assessment.progress": "Soru {current} / {total}",
        "assessment.previous_yes": "Önceki yanıt: Evet",
        "assessment.previous_no": "Önceki yanıt: Hayır",
        "assessment.no": "Hayır",
        "assessment.yes": "Evet",
        "assessment.back": "Geri",
        "assessment.reset": "Sıfırla",
        "assessment.done_title": "Tüm etkinlik kartları tamamlandı",
        "assessment.done_text": "Kariyer eşleşmelerini oluşturmak için hazırlık düzeylerini seç.",
        "assessment.completed": "{answered} / {total} kart yanıtlandı",
        "assessment.submit": "Eşleşmelerimi oluştur",
        "assessment.spinner": "Eşleşmelerin oluşturuluyor...",
        "assessment.incomplete": "Eşleşmeleri oluşturmadan önce tüm etkinlik kartlarını yanıtla.",
        "assessment.flat_profile": (
            "Altı ilgi alanının hepsinde aynı sonucu aldın, bu yüzden kariyer eşleştirilemiyor. "
            "Yanıtlarını gözden geçir ya da başka bir zaman tekrar dene."
        ),
        "assessment.saved": "Profil, kart seçimlerinden güncellendi.",
        "profile.ready": "Profil hazır",
        "profile.code": "Kariyer kodu",
        "profile.current_zone": "Mevcut bölge",
        "profile.future_zone": "Hedef bölge",
        "followup.kicker": "İyileştir",
        "final.kicker": "Rapor",
        "report.alternative.reason": "Gönderdiğin Interest Profiler eşleşmeleriyle ilgili bir kariyer.",
        "report.ai_summary.resolved": " O*NET ve yapay zekâ verisi {resolved_title} mesleğinden alındı.",
        "report.ai_summary.exposure": (
            "Anthropic'in yerel meslek verisi, eşleştirilen O*NET mesleği için gözlemlenen maruziyeti {value} "
            "olarak gösteriyor {marker}."
        ),
        "report.ai_summary.task_rows": (
            "Eşleştirilen meslek için Anthropic görev verisi, O*NET görev numarasıyla birebir bulundu {marker}."
        ),
        "report.ai_summary.no_rows": "Gösterilen O*NET görevleri için yerel Anthropic görev verisi bulunamadı.",
        "report.ai_summary.role": (
            "Benim yorumum, yapay zekânın mesleğin tamamının yerini almaktan çok, işin tekrarlanan, yazı ağırlıklı "
            "veya dijital kısımlarında yardımcı olma olasılığının daha yüksek olduğu yönünde. İşin muhakeme, "
            "bağlam, kalite kontrolü, sorumluluk ve iyi bir sonucun neye benzediğini bilmeyi gerektirdiği yerlerde "
            "insan katkısı hâlâ en önemli kısım."
        ),
        "report.ai_summary.context": (
            "Üretken yapay zekânın genel benimsenmesine dair veriler, görev düzeyinde puanlama için değil, işgücü "
            "piyasası bağlamı olarak kullanılır {marker}."
        ),
        "report.day.no_tasks": (
            "Bulunan verilerden bu mesleğin günlük akışını çıkarmak zor; karar vermeden önce mesleğe özgü biraz "
            "daha araştırma yapmakta fayda var."
        ),
        # Turkish only: the English fallback rebuilds the tasks into a sentence with English grammar.
        "report.day.tasks": "Bu meslekte bir gün genellikle şu işler etrafında şekillenir: {tasks}.",
        "source.ip.title": "O*NET Interest Profiler kısa formu ve kariyer eşleştirme kuralı",
        "source.ip.section": (
            "RIASEC puanları, Holland kodu, İş Bölgesi seçimleri; O*NET kuralına göre kariyer eşleştirme "
            "(ilgi profili korelasyonu, en iyi / çok iyi / iyi uyum)"
        ),
        "source.ip.note": "Kısa form: {short_form}; eşleştirme kuralı (Gregory ve Lewis 2016): {rule}",
        "source.onet.title": "O*NET meslek verisi - {title}",
        "source.onet.section": (
            "tanım, görevler, beceriler, bilgi alanları, yetenekler, eğitim, İş Bölgesi, çalışma ortamı, "
            "yazılımlar, ilgili meslekler"
        ),
        "source.onet.alias_section": "meslek adı, O*NET-SOC eşleştirmesi ve İş Bölgesi",
        "source.onet.note": "O*NET-SOC {code}",
        "source.anthropic.title": "Anthropic Economic Index ve işgücü piyasası etkileri",
        "source.anthropic.section": "meslek ve görev düzeyinde gözlemlenen maruziyet ve görev kapsamı verileri",
        "source.anthropic.note": (
            "Görev verileri yalnızca eşleştirilen O*NET-SOC koduna ve birebir O*NET görev numarasına uyduğunda "
            "kullanılır."
        ),
        "source.nber.section": "üretken yapay zekânın genel benimsenme bağlamı",
        "source.nber.note": (
            "Görev düzeyinde otomasyon puanı olarak değil, genel işgücü piyasası ve benimsenme bağlamı olarak "
            "kullanıldı."
        ),
        "source.usage.title": "Anthropic Economic Index, 2026-06-26 sürümü (Claude.ai, meslek bazında)",
        "source.usage.section": "{month} için soc_occupation satırları, GLOBAL ve TUR",
        "source.usage.note": "Türkiye değeri yoksa Anthropic onu yayımlamamıştır (örneklem eşiğinin altında).",
        "source.research.note": (
            "Bulgular anlam benzerliğiyle eşleştirildi, ardından bir dil modeliyle ilgililik açısından kontrol "
            "edildi (CHANGELOG 032)."
        ),
        "report.alternatives.header": "Alternatif Kariyerler",
        "report.alternatives.none": "Yerel O*NET kanıtlarından alternatif çözümlenemedi.",
        "report.sources.header": "Kaynaklar",
        "report.sources.expander": "Numaralı atıfları görüntüle",
        # Shown only in Turkish: O*NET's CC BY 4.0 licence asks that changes, such as a translation, be marked.
        "report.sources.translation_note": (
            "Meslek adları, tanımlar, görevler, beceriler ve İş Bölgesi metinleri O*NET'ten (ABD Çalışma "
            "Bakanlığı, CC BY 4.0) alınmış ve bu uygulama için bir yapay zekâ modeliyle Türkçeye çevrilmiştir; "
            "bu bir uyarlamadır. Araştırma bulguları da çevrilmiştir, alıntılar ise orijinal dilindedir. "
            "Orijinal metinler için kaynak bağlantılarına bak."
        ),
        "report.no_local_evidence": "Bu bölüm için yerel kanıt getirilemedi.",
        "report.skills.software": "Yazılım / teknik araçlar",
        "report.skills.technical": "Teknik ve alan becerileri",
        "report.skills.foundational": "Temel iletişim",
        "report.skills.knowledge": "Bilgi alanları",
        "report.skills.in_demand": "Aranan",
        "report.preferences.tasks": "Görevler ve araçlar",
        "report.preferences.work_style": "Çalışma tarzı",
        "report.preferences.people": "İnsanlar ve ortam",
        "report.preferences.direction": "Kariyer yönü",
        "report.preferences.other": "Diğer",
        "report.education.typical": "Tipik hazırlık: ",
        "report.education.training": "Deneyim ve eğitim: ",
        "report.education.responses": "O*NET eğitim yanıtları",
        "report.education.none": "Bu bölüm için yerel eğitim veya İş Bölgesi kanıtı getirilemedi.",
        "report.job_zone.unavailable": "İş Bölgesi kullanılamıyor",
        "report.job_zone.preparation_unavailable": "hazırlık düzeyi kullanılamıyor",
        "report.job_zone.title": "İş Bölgesi {zone} ({explanation})",
        "report.job_zone.typical_education": "tipik eğitim: {education}",
        "report.job_zone.training": "hazırlık: {training}",
        "report.career_fallback": "Kariyer",
        "report.education.master_with_bachelor": (
            "O*NET yanıtlarının çoğu bu rol için yüksek lisans derecesine işaret ediyor; "
            "lisans derecesi yolları da var ancak daha az yaygın."
        ),
        "report.education.master": "O*NET yanıtlarının çoğu bu rol için yüksek lisans derecesine işaret ediyor.",
        "report.education.bachelor_with_master": (
            "O*NET yanıtlarının çoğu lisans derecesine işaret ediyor; yüksek lisans düzeyi hazırlık da yaygın."
        ),
        "report.education.bachelor": "O*NET yanıtlarının çoğu bu rol için lisans derecesine işaret ediyor.",
        "report.education.doctoral": (
            "O*NET yanıtlarının çoğu bu rol için doktora veya profesyonel derece hazırlığına işaret ediyor."
        ),
        "report.education.associate": (
            "O*NET yanıtlarının çoğu bu rol için ön lisans veya mesleki hazırlığa işaret ediyor."
        ),
        "report.education.high_school": (
            "O*NET yanıtlarının çoğu bu rol için lise düzeyi hazırlığa işaret ediyor."
        ),
        "report.education.dynamic": "O*NET yanıtlarının çoğu bu rol için {label} düzeyine işaret ediyor.",
        "common.na": "Yok",
    },
}


INTEREST_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "Realistic": "Realistic",
        "Investigative": "Investigative",
        "Artistic": "Artistic",
        "Social": "Social",
        "Enterprising": "Enterprising",
        "Conventional": "Conventional",
    },
    "tr": {
        "Realistic": "Gerçekçi",
        "Investigative": "Araştırmacı",
        "Artistic": "Sanatsal",
        "Social": "Sosyal",
        "Enterprising": "Girişimci",
        "Conventional": "Geleneksel",
    },
}


# O*NET's Job Zone names (job_zone_reference). Since O*NET 30.3, zones 1 and 2 are one
# zone, "Job Zone 1-2", stored as 2; a 1 from an older saved profile is read as 2.
JOB_ZONE_LABEL_TRANSLATIONS: dict[str, dict[int, str]] = {
    "en": {
        2: "Very Little to Some Preparation Needed",
        3: "Medium Preparation Needed",
        4: "Considerable Preparation Needed",
        5: "Extensive Preparation Needed",
    },
    "tr": {
        2: "Çok Az veya Biraz Hazırlık Gerekir",
        3: "Orta Düzey Hazırlık Gerekir",
        4: "Önemli Ölçüde Hazırlık Gerekir",
        5: "Kapsamlı Hazırlık Gerekir",
    },
}


# Our short paraphrase of O*NET's job_zone_reference "education" sentence (D13 = C).
# O*NET says "usually" / "most", never "required": e.g. Zone 4 is "Most of these
# occupations require a four-year bachelor's degree, but some do not."
JOB_ZONE_PREPARATION_TRANSLATIONS: dict[str, dict[int, str]] = {
    "en": {
        2: "usually a high school diploma",
        3: "usually vocational training, work experience or an associate's degree",
        4: "usually a bachelor's degree",
        5: "usually a graduate degree",
    },
    "tr": {
        2: "genellikle lise diploması",
        3: "genellikle mesleki eğitim, iş deneyimi veya ön lisans",
        4: "genellikle lisans derecesi",
        5: "genellikle lisansüstü eğitim",
    },
}


QUESTION_TRANSLATIONS: dict[str, dict[int, str]] = {
    "tr": {
        1: "Mutfak dolapları yapmak",
        2: "Ofislere ve evlere paket teslim etmek için kamyon kullanmak",
        3: "Tuğla veya karo döşemek",
        4: "Sevkiyattan önce parçaların kalitesini test etmek",
        5: "Ev aletlerini onarmak",
        6: "Kilitleri onarmak ve takmak",
        7: "Balık üretim çiftliğinde balık yetiştirmek",
        8: "Ürün yapmak için makineleri kurmak ve çalıştırmak",
        9: "Elektronik parçaları monte etmek",
        10: "Orman yangınlarını söndürmek",
        11: "Yeni bir ilaç geliştirmek",
        12: "Bir yangının nedenini araştırmak",
        13: "Su kirliliğini azaltmanın yollarını incelemek",
        14: "Hava durumunu daha iyi tahmin etmenin bir yolunu geliştirmek",
        15: "Kimyasal deneyler yapmak",
        16: "Biyoloji laboratuvarında çalışmak",
        17: "Gezegenlerin hareketini incelemek",
        18: "Şekerin yerine geçecek bir madde icat etmek",
        19: "Kan örneklerini mikroskopla incelemek",
        20: "Hastalıkları belirlemek için laboratuvar testleri yapmak",
        21: "Kitaplar veya tiyatro oyunları yazmak",
        22: "Tiyatro oyunları için dekor boyamak",
        23: "Bir müzik aleti çalmak",
        24: "Film veya televizyon programları için senaryo yazmak",
        25: "Müzik bestelemek veya düzenlemek",
        26: "Caz veya tap dansı yapmak",
        27: "Resim çizmek",
        28: "Bir grupta şarkı söylemek",
        29: "Filmler için özel efektler yaratmak",
        30: "Filmleri kurgulamak",
        31: "Bir kişiye egzersiz rutini öğretmek",
        32: "Çocuklara spor yapmayı öğretmek",
        33: "Kişisel veya duygusal sorunları olan insanlara yardım etmek",
        34: "Sağır veya işitme güçlüğü çeken kişilere işaret dili öğretmek",
        35: "İnsanlara kariyer rehberliği yapmak",
        36: "Bir grup terapisi oturumunun yürütülmesine yardım etmek",
        37: "Rehabilitasyon terapisi uygulamak",
        38: "Gündüz bakımevinde çocuklarla ilgilenmek",
        39: "Kar amacı gütmeyen bir kuruluşta gönüllü çalışma yapmak",
        40: "Lise sınıfında ders vermek",
        41: "Hisse senedi ve tahvil alıp satmak",
        42: "İş sözleşmeleri müzakere etmek",
        43: "Bir perakende mağazasını yönetmek",
        44: "Bir davada müvekkili temsil etmek",
        45: "Güzellik salonu veya berber dükkanı işletmek",
        46: "Yeni bir giyim serisini pazarlamak",
        47: "Büyük bir şirkette bir departmanı yönetmek",
        48: "Bir mağazada ürün satmak",
        49: "Kendi işini kurmak",
        50: "Bir giyim mağazasını yönetmek",
        51: "Bilgisayar yazılımı kullanarak elektronik tablo hazırlamak",
        52: "Çalışanların ücretlerini hesaplamak",
        53: "Kayıtları veya formları kontrol edip düzeltmek",
        54: "El bilgisayarı kullanarak malzeme envanteri çıkarmak",
        55: "Büyük bir ağdaki bilgisayarlara yazılım kurmak",
        56: "Kira ödemelerini kaydetmek",
        57: "Hesap makinesi kullanmak",
        58: "Envanter kayıtlarını tutmak",
        59: "Gönderim ve teslim alma kayıtlarını tutmak",
        60: "Bir kuruluş için postaları damgalamak, ayırmak ve dağıtmak",
    }
}


FOLLOWUP_QUESTION_TRANSLATIONS: dict[str, dict[str, str]] = {
    "tr": {
        "work_setting": (
            "Çalışma saatlerini en çok nerede geçirmek isterdin? Fiziksel alanı, atmosferi, "
            "iç mekan mı dış mekan mı olduğunu düşün; ideal çalışma ortamını gözünde canlandırıp anlat."
        ),
        "work_with": (
            "Kendini sevdiğin bir işe tamamen kaptırmış halde hayal ettiğinde aslında ne yapıyorsun? "
            "İş unvanı değil; odada neler oluyor, neyle veya kimlerle etkileşiyorsun?"
        ),
        "independence": (
            "İşte veya okulda kendini en özgür ve etkili hissettiğin bir zamanı anlat. Bunu iyi yapan "
            "neydi: kendi başına mıydın, iş birliği mi yapıyordun, bir yapıyı mı takip ediyordun, "
            "yoksa yolu kendin mi buluyordun?"
        ),
        "team_dynamic": (
            "Günlük olarak başka insanlarla çalışmak sana nasıl geliyor? Enerji mi veriyor, yoruyor mu? "
            "İşinde ideal insan etkileşimi miktarı ve türü nedir?"
        ),
        "impact_type": (
            "Gerçekten iyi bir iş gününün sonunda, yaptığın işin önemli olduğunu sana ne hissettirirdi? "
            "Çalışmanın ne tür bir fark yaratmasını istersin?"
        ),
        "structure_preference": (
            "Gününün net bir ajandası veya planı olmadığında nasıl hissediyorsun? Tersine, her saatin "
            "senin için planlandığında nasıl hissediyorsun?"
        ),
        "skill_anchor": (
            "Okulda, işte, bir projede veya herhangi bir yerde yaptığın ve birinin 'bunda gerçekten iyisin' "
            "dediği, senin de buna inandığın bir şeyi anlat. Ne yapıyordun?"
        ),
        "recognition": (
            "Ne tür bir takdir veya sonuç çalışmanı değerli hissettirir? Görünür bir çıktı mı, uzman "
            "olarak görülmek mi, birinin minnettarlığı mı, yoksa bambaşka bir şey mi?"
        ),
        "future_concern": (
            "Kariyer geleceğini düşündüğünde seni en çok ne endişelendiriyor? Maaş gibi pratik şeyler "
            "değil; yanlış seçim yapmayı hayal ettiğinde ortaya çıkan daha derin korku nedir?"
        ),
        "dream_scenario": (
            "Beş yıl sonra, seni iyi tanıyan biriyle karşılaşıyorsun ve ona neler yaptığını anlatıyorsun. "
            "Ona ne anlatıyor olmak isterdin?"
        ),
    }
}


DISPLAY_TRANSLATIONS: dict[str, dict[str, str]] = {
    "tr": {
        "Current Job Zone options": "Mevcut İş Bölgesi seçenekleri",
        "Future Job Zone options": "Hedeflenen İş Bölgesi seçenekleri",
        "Best fit": "En iyi uyum",
        "Great fit": "Çok iyi uyum",
        "Good fit": "İyi uyum",
        "Tasks and tools": "Görevler ve araçlar",
        "Work style": "Çalışma tarzı",
        "People and setting": "İnsanlar ve ortam",
        "Career direction": "Kariyer yönü",
        "Other": "Diğer",
        "onet": "O*NET",
        "ai_impact": "Yapay zekâ etkisi",
        "Covered": "Kapsanıyor",
        "Covered: mostly automation": "Kapsanıyor: çoğunlukla otomasyon",
        "Covered: mostly augmentation": "Kapsanıyor: çoğunlukla destekleme",
        "Covered: mixed": "Kapsanıyor: karma",
        "Not covered": "Kapsanmıyor",
        "No data": "Veri yok",
    }
}


ARTIFACT_LABEL_TRANSLATIONS: dict[str, dict[str, str]] = {
    "tr": {
        "onet_duckdb": "O*NET DuckDB veritabanı",
        "ai_impact_duckdb": "Yapay zekâ etkisi DuckDB veritabanı",
        "research_claims": "Meslek başına araştırma bulguları",
        "content_translations": "Türkçe kariyer içeriği",
        "ilo_exposure": "Kariyer başına ILO maruziyeti",
    }
}


def normalize_language(language: Any) -> str:
    """Return a supported language code."""
    value = str(language or DEFAULT_LANGUAGE).strip().lower()
    if value in {"tr", "tur", "turkish", "turkce", "türkçe"}:
        return "tr"
    return DEFAULT_LANGUAGE


def ui_text(key: str, language: Any = DEFAULT_LANGUAGE, **format_values: Any) -> str:
    """Return translated UI text, falling back to the exact English string."""
    normalized = normalize_language(language)
    value = TEXT.get(normalized, {}).get(key) or TEXT[DEFAULT_LANGUAGE].get(key) or key
    return value.format(**format_values) if format_values else value


# Turkish names for the O*NET education categories that have no sentence of their own
# (ROADMAP 2.10); English uses O*NET's own name.
EDUCATION_CATEGORY_NAMES: dict[str, dict[int, str]] = {
    "tr": {
        1: "lise diplomasının altındaki eğitim",
        3: "lise sonrası sertifika",
        4: "bir miktar üniversite dersi",
        7: "lisans sonrası sertifika",
        9: "yüksek lisans sonrası sertifika",
    },
}


def education_category_name(category: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """Localized name of an O*NET education category, or "" to use O*NET's English name."""
    try:
        return EDUCATION_CATEGORY_NAMES.get(normalize_language(language), {}).get(int(category), "")
    except (TypeError, ValueError):
        return ""

MONTH_NAMES: dict[str, list[str]] = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
    "tr": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos",
           "Eylül", "Ekim", "Kasım", "Aralık"],
}


def month_label(iso_date: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """ "2026-05-01" -> "May 2026" / "Mayıs 2026"."""
    year, month = str(iso_date)[:7].split("-")
    return f"{MONTH_NAMES[normalize_language(language)][int(month) - 1]} {year}"


def percent_text(value: float, language: Any = DEFAULT_LANGUAGE) -> str:
    """ "0.35%" in English, "%0,35" in Turkish (Turkish puts % first and uses a decimal comma)."""
    number = f"{value:g}"
    if normalize_language(language) == "tr":
        return "%" + number.replace(".", ",")
    return number + "%"


# The ILO's exposure groups (Working Paper 140, Table 5, p. 41): a short name and the ILO's own interpretation.
ILO_GRADIENTS: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "Gradient 4": ("Highest exposure (ILO gradient 4)",
                       "most tasks have a high potential to be automated with generative AI, with little variation between them"),
        "Gradient 3": ("Significant exposure (ILO gradient 3)",
                       "some tasks remain less exposed, but the potential to automate the current tasks is growing"),
        "Gradient 2": ("Moderate exposure (ILO gradient 2)",
                       "a mix of tasks exposed to generative AI and tasks not at risk, so the impact is uneven"),
        "Gradient 1": ("Low exposure with some exposed tasks (ILO gradient 1)",
                       "the work relies mostly on tasks with low potential, but some tasks have an elevated one"),
        "Minimal Exposure": ("Minimal exposure", "low exposure overall; some tasks show moderate potential"),
        "Not Exposed": ("Not exposed", "most tasks remain relatively unaffected by generative AI"),
    },
    "tr": {
        "Gradient 4": ("En yüksek maruziyet (ILO derecesi 4)",
                       "görevlerin çoğunun üretken yapay zekâ ile otomasyon potansiyeli yüksek ve görevler arasında fark az"),
        "Gradient 3": ("Önemli maruziyet (ILO derecesi 3)",
                       "bazı görevler daha az etkileniyor, ancak mevcut görevlerin otomasyon potansiyeli artıyor"),
        "Gradient 2": ("Orta maruziyet (ILO derecesi 2)",
                       "üretken yapay zekâya açık görevlerle risk altında olmayan görevlerin karışımı; etki eşit değil"),
        "Gradient 1": ("Düşük maruziyet, bazı görevler açık (ILO derecesi 1)",
                       "iş çoğunlukla potansiyeli düşük görevlere dayanıyor, ancak bazı görevlerin potansiyeli yüksek"),
        "Minimal Exposure": ("Asgari maruziyet", "genel olarak düşük maruziyet; bazı görevlerde orta düzey potansiyel var"),
        "Not Exposed": ("Maruz değil", "görevlerin çoğu üretken yapay zekâdan görece etkilenmiyor"),
    },
}


def ilo_exposure_lines(ilo: dict[str, Any], language: str = "en") -> list[str]:
    """The ILO panel's sentences (D5 = B): the exposure group and its meaning, the scores, the group it
    belongs to, and what kind of evidence it is. No combined score with the Claude data."""
    language = normalize_language(language)
    name, meaning = ILO_GRADIENTS[language][ilo["gradient"]]

    def number(value: float) -> str:
        text = f"{value:.2f}"
        return text.replace(".", ",") if language == "tr" else text

    title = content_text(ilo["isco08_title"], language)
    others = ilo["careers_in_group"] - 1
    scope = (ui_text("report.ilo.scope", language, code=ilo["isco08_code"], title=title, others=others) if others
             else ui_text("report.ilo.scope_single", language, code=ilo["isco08_code"], title=title))
    return [
        f"{name}: {meaning}.",
        ui_text("report.ilo.score", language, mean=number(ilo["mean"]), sd=number(ilo["sd"])),
        scope,
        ui_text("report.ilo.meaning", language),
    ]


def claude_usage_lines(usage: dict[str, Any], language: str = "en") -> list[str]:
    """Fixed sentences for the Anthropic usage block (D14 = C); no LLM translation needed."""

    def share(value: float) -> str:
        # Anthropic rounds to two decimals, so 0.0 means "below 0.01%", not zero.
        if value == 0:
            return ui_text("report.usage.below", language, value=percent_text(0.01, language))
        return percent_text(value, language)

    lines = [ui_text("report.usage.share", language, global_pct=share(usage["global_pct"]))]
    if usage.get("turkey_pct") is None:
        lines.append(ui_text("report.usage.share_turkey_missing", language))
    else:
        lines.append(ui_text("report.usage.share_turkey", language, turkey_pct=share(usage["turkey_pct"])))
    lines.append(ui_text("report.usage.share_note", language))
    if usage.get("automation_pct") is not None and usage.get("augmentation_pct") is not None:
        lines.append(
            ui_text(
                "report.usage.split",
                language,
                automation_pct=percent_text(round(usage["automation_pct"]), language),
                augmentation_pct=percent_text(round(usage["augmentation_pct"]), language),
            )
        )
    if usage.get("human_only_hours") is not None and usage.get("with_ai_minutes") is not None:
        hours = f"{usage['human_only_hours']:.1f}"
        lines.append(
            ui_text(
                "report.usage.time",
                language,
                hours=hours.replace(".", ",") if normalize_language(language) == "tr" else hours,
                minutes=round(usage["with_ai_minutes"]),
            )
        )
    return lines


def question_text(question: dict[str, Any], language: Any = DEFAULT_LANGUAGE) -> str:
    """Return the localized Interest Profiler question text for display."""
    normalized = normalize_language(language)
    question_id = question.get("id")
    try:
        numeric_id = int(question_id)
    except (TypeError, ValueError):
        numeric_id = -1
    return QUESTION_TRANSLATIONS.get(normalized, {}).get(numeric_id) or str(question.get("text") or "")


def followup_question_text(question: dict[str, Any], language: Any = DEFAULT_LANGUAGE) -> str:
    """Return the localized follow-up question text for display."""
    normalized = normalize_language(language)
    question_id = str(question.get("id") or "").strip()
    return FOLLOWUP_QUESTION_TRANSLATIONS.get(normalized, {}).get(question_id) or str(
        question.get("question") or ""
    )


def interest_label(interest: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """Return a localized RIASEC interest name for display."""
    text = str(interest or "")
    normalized = normalize_language(language)
    return INTEREST_TRANSLATIONS.get(normalized, {}).get(text) or text


def job_zone_number(zone: Any) -> str:
    """How a Job Zone is numbered for users: O*NET's merged zone 1-2 shows as "1-2"."""
    return "1-2" if str(zone) in {"1", "2"} else str(zone or "")


def job_zone_label(zone: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """Return a localized O*NET Job Zone label."""
    try:
        zone_int = max(int(zone), 2)
    except (TypeError, ValueError):
        return str(zone or "")
    normalized = normalize_language(language)
    return JOB_ZONE_LABEL_TRANSLATIONS.get(normalized, {}).get(
        zone_int,
        JOB_ZONE_LABEL_TRANSLATIONS[DEFAULT_LANGUAGE].get(zone_int, str(zone_int)),
    )


def job_zone_preparation(zone: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """Return a localized preparation explanation for a Job Zone."""
    try:
        zone_int = max(int(zone), 2)
    except (TypeError, ValueError):
        return ui_text("report.job_zone.preparation_unavailable", language)
    normalized = normalize_language(language)
    return JOB_ZONE_PREPARATION_TRANSLATIONS.get(normalized, {}).get(
        zone_int,
        ui_text("report.job_zone.preparation_unavailable", language),
    )


def display_label(value: Any, language: Any = DEFAULT_LANGUAGE) -> str:
    """Translate known generated labels while leaving unknown data untouched."""
    text = str(value or "")
    normalized = normalize_language(language)
    return DISPLAY_TRANSLATIONS.get(normalized, {}).get(text) or text


def artifact_label(artifact: dict[str, Any], language: Any = DEFAULT_LANGUAGE) -> str:
    """Return a localized artifact label for missing-artifact UI."""
    normalized = normalize_language(language)
    artifact_id = str(artifact.get("id") or "")
    return ARTIFACT_LABEL_TRANSLATIONS.get(normalized, {}).get(artifact_id) or str(
        artifact.get("label") or artifact_id
    )


def content_text(value: Any, language: Any = DEFAULT_LANGUAGE, context: str = "O*NET content") -> str:
    """O*NET content or a research claim in the display language, from the build-time table (ROADMAP 6.1c).

    Text not in the table (software names, for instance) is shown as it is; nothing is translated at runtime.
    """
    del context  # kept for readability at call sites
    text = str(value or "").strip()
    if normalize_language(language) != "tr" or not text:
        return text
    return _content_translations().get(" ".join(text.split())) or text


@lru_cache(maxsize=1)
def _content_translations() -> dict[str, str]:
    """{English: Turkish} from data/i18n/content_tr.csv (scripts/i18n/translate_content.py)."""
    import csv

    with CONTENT_TRANSLATIONS_PATH.open(encoding="utf-8", newline="") as handle:
        return {row["english"]: row["turkish"] for row in csv.DictReader(handle)}
