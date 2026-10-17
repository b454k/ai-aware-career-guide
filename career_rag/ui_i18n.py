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
        "app.method_references": "Method references",
        "initial.instructions": (
            "Check the box by the activities you would like to do. Do not think about "
            "how much education/training is needed or how much money you will make."
        ),
        "initial.activities_header": "{count} Work Activities",
        "initial.job_zone_header": "Job Zone Questions",
        "initial.current_job_zone_heading": "A. Current Job Zone",
        "initial.current_job_zone_question": (
            "What level of education, training, and experience do you currently have?"
        ),
        "initial.future_job_zone_heading": "B. Future Job Zone",
        # The department question (ROADMAP 9.1).
        "initial.department_question": "Which department do you study in?",
        "initial.department_placeholder": "Choose your department",
        "initial.department_help": "Your careers come from your department, ranked by your answers. If it isn't listed, choose the last option and pick a preparation level instead.",
        "initial.department_other": "My department isn't listed",
        "profile.department": "Department",
        "initial.future_job_zone_question": (
            "What level of education, training, and experience are you willing to work toward?"
        ),
        "initial.submit": "Submit",
        "followup.header": "Refine the order (optional)",
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
        "artifacts.missing_title": "RAG artifacts missing. Please run the setup/build command.",
        "artifacts.missing_list": "Missing or unusable artifacts:",
        "artifacts.rebuild": "Rebuild artifacts from raw/local sources:",
        "artifacts.verify": "Then verify:",
        "report.summary.preferences": "Preferences Used For Matching",
        "report.top_matches.caption": (
            "This report shows up to five careers for your current Job Zone and up to five "
            "careers for the future Job Zone you are willing to work toward."
        ),
        "report.top_matches.caption_department": "These are your department's careers, ranked by how well they fit your answers.",
        "report.guidance.department": "These careers come from your department; the ones that fit your answers best come first.",
        "report.top_matches.fit": "Fit",
        "report.job.what_does": "What This Job Does",
        "report.job.no_description": "No local O*NET description was retrieved.",
        "report.job.main_tasks": "Main Tasks",
        "report.job.key_skills": "Key Skills",
        "report.job.education_zone": "Education / Job Zone",
        "report.job.ai_impact": "AI Impact Breakdown",
        "report.job.day_life": "Day In The Life",
        "report.ai.caption": (
            "Task coverage comes from Anthropic's labor-market impacts data (Claude usage in "
            "August and November 2025). A task counts as covered when it had enough work-related "
            "Claude usage and is a task language models can do. \"Mostly automation\" means Claude "
            "mostly does the task; \"mostly augmentation\" means people mostly work through it with "
            "Claude. Covered does not mean the job will disappear. "
            "Not covered does not mean the task is safe from AI either: it only means this Claude data "
            "did not show it, and it says nothing about other AI tools, robots or future models. "
            "No data means Anthropic has no row for this exact O*NET task, which is not the same as "
            "not covered."
        ),
        "report.ai.no_rows": "No AI impact rows were available for this occupation.",
        # About the data, said once (ROADMAP 9.5).
        "app.caption": (
            "A career guide for university students: it suggests careers from your department and your interests, "
            "and shows what the evidence says about AI and each job, including where there is none."
        ),
        "report.tab.about": "About the data",
        "about.careers.title": "Where the careers come from",
        "about.careers.text": (
            "Your department's careers come from the US fields of study it corresponds to, through the official "
            "field-of-study to occupation crosswalk of the US education statistics office (NCES), reviewed by "
            "hand. Without a department, they come from O\\*NET's own matching rule over every occupation at your "
            "chosen preparation levels. Either way they are ranked by how closely your interest scores match each "
            "career's (O\\*NET's Interest Profiler rule). The alternatives are the best fits by the same rule at every "
            "preparation level, outside your list. The careers and their descriptions are from O\\*NET, which "
            "describes US jobs."
        ),
        "about.picture.title": "The AI picture",
        "about.picture.text": (
            "Each career's AI picture compares two sources and never averages them: how many of its main tasks "
            "people already use Claude for, and how exposed experts rate this kind of work (ILO). When they "
            "agree, it says so; when they disagree, it says that too."
        ),
        "about.anthropic.title": "Claude use (Anthropic)",
        "about.anthropic.estimates": (
            "How much people use Claude for a job shows use, not how many jobs change. Anthropic's time estimates "
            "come from a model reading conversations, not from measured productivity."
        ),
        "about.ilo.title": "Experts' rating (ILO)",
        "about.ilo.text": (
            "The International Labour Organization rates each occupation group's tasks for their potential "
            "exposure to generative AI, from surveys, experts and a model. It is an assessment, not observed use, "
            "so it can differ from the Claude data, and it describes a broader group of occupations than one "
            "career."
        ),
        "about.research.title": "Research findings",
        "about.next.title": "Next steps",
        "about.next.text": (
            "Each career's next steps follow one rule, from its own data. First, its tools that US job postings "
            "ask for (O\\*NET's in-demand software), those asked for in the fewest other occupations first, leaving "
            "out general office software such as Excel; a career without them gets the two knowledge areas it "
            "relies on most. Then, if people already use Claude for one of its main tasks, that task. Last, its "
            "most important other task, to try in an internship or a course project."
        ),
        # The AI snapshot on each career (ROADMAP 9.2).
        "snapshot.chip": "AI use seen: {seen} of {total} tasks",
        "snapshot.chip_none": "No AI task data",
        "snapshot.claude.seen": "People use Claude for {seen} of this job's {total} main tasks (Anthropic, 2025).",
        "snapshot.claude.zero": "No Claude use was seen for any of this job's {total} main tasks (Anthropic, 2025).",
        "snapshot.claude.none": "There is no Claude task data for this job.",
        "snapshot.ilo.high": "Experts rate this kind of work as highly exposed to generative AI (ILO).",
        "snapshot.ilo.medium": "Experts rate this kind of work as moderately exposed to generative AI (ILO).",
        "snapshot.ilo.low": "Experts rate this kind of work as little exposed to generative AI (ILO).",
        "snapshot.ilo.none": "There is no expert rating for this kind of work.",
        "snapshot.research.many": "{count} research findings about this career, in the details.",
        "snapshot.research.one": "One research finding about this career, in the details.",
        "snapshot.research.none": "No study in our collection is about this career yet.",
        "snapshot.verdict.high_reach": "AI already reaches much of this work: expect its tasks to change.",
        "snapshot.verdict.low_reach": "The sources show little AI reach into this work so far, which is not the same as safe from AI.",
        "snapshot.verdict.disagree_unseen": "The sources disagree: no Claude use was seen for these tasks, but experts rate the work as exposed. Not seen does not mean safe.",
        "snapshot.verdict.disagree_used": "The sources disagree: people already use Claude for many of these tasks, though experts rate the work as less exposed.",
        "snapshot.verdict.partial": "AI reaches parts of this work, not all of it.",
        "snapshot.verdict.none": "Our sources have no AI evidence for this job.",
        # The comparison table (ROADMAP 9.3).
        "report.compare.career": "Career",
        "report.compare.fit": "Fit",
        "report.compare.picture": "AI picture",
        "snapshot.short.high_reach": "much AI reach",
        "snapshot.short.low_reach": "little so far",
        "snapshot.short.disagree_unseen": "sources disagree",
        "snapshot.short.disagree_used": "sources disagree",
        "snapshot.short.partial": "partly",
        "snapshot.short.none": "no data",
        "report.usage.title": "How people use Claude for this work ({month})",
        "report.usage.share": "{global_pct} of all Claude.ai conversations worldwide were about this occupation's tasks.",
        "report.usage.share_turkey": "In Turkey: {turkey_pct}.",
        "report.usage.share_turkey_missing": "Turkey: not published (fewer conversations than Anthropic's threshold).",
        "report.usage.split": (
            "{automation_pct} automation-style (Claude carries out the task), "
            "{augmentation_pct} augmentation-style (the person works through it with Claude)."
        ),
        "report.usage.time": "Anthropic's estimate: about {hours} hours for a person alone, about {minutes} minutes with AI.",
        "report.usage.below": "under {value}",
        "report.ilo.title": "How exposed this kind of work is to generative AI (ILO)",
        "report.ilo.scope": (
            "This is the ILO's score for the broader ISCO-08 group {code} \"{title}\", which also covers "
            "{others} other careers in this app."
        ),
        "report.ilo.scope_single": "This is the ILO's score for the ISCO-08 group {code} \"{title}\".",
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
            "Claims from the reports and papers on AI and work in our collection, matched to each career by similarity "
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
        "report.why.interests_shared": "Its strongest interest areas, {career}, are both among yours ({student}). {marker}",
        "report.why.interests_one": "Of its two strongest interest areas ({career}), {shared} is among yours ({student}). {marker}",
        "report.why.interests_other": (
            "Its strongest interest areas, {career}, are not among your top three ({student}), "
            "so it fits your answers less well. {marker}"
        ),
        "report.why.activities": "Activities you said yes to that match this work: {activities}.",
        "report.why.department": "It is one of the careers your department leads to.",
        "report.guidance.default": (
            "Use future job zone for aspirational recommendations, current job zone for immediate options."
        ),
        # The follow-up agent's note (ip_followup_agent.py), word for word.
        "report.guidance.followup": (
            "Use the original O*NET Interest Profiler matches as the candidate pool, "
            "then rank them by the open-ended filtering answers and O*NET occupation signals."
        ),
        "report.resolution_note": "Displayed as {display_title}; O*NET evidence retrieved from {resolved_title}.",
        # The card test and profile screens (moved from interest_profiler_app.py, ROADMAP 7.1).
        "hero.status": "Interest profile",
        "results.header": "Your results",
        # Next steps per career, by a stated rule (ROADMAP 9.7).
        "report.next.tools": "Learn the tools job postings for this career ask for: {tools} (O*NET).",
        "report.next.knowledge": "Build the knowledge this job relies on most: {areas} (O*NET).",
        "report.next.ai": "People already use Claude for “{task}”: practise it with an AI tool, and learn to catch its mistakes.",
        "report.next.try": "Try the work before you choose: look for an internship or a course project that includes “{task}”.",
        "results.change_answers": "Change my answers",
        "results.back": "Back to my results",
        "assessment.header": "Start with quick swipes",
        "assessment.test": "Test length",
        "assessment.test.mini_ip_30": "Quick: 30 activities",
        "assessment.test.short_form_60": "Full: 60 activities",
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
        "profile.code": "Career code",
        "profile.current_zone": "Current zone",
        "profile.future_zone": "Future zone",
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
        "source.onet.note": "O*NET-SOC {code}",
        "source.anthropic.title": "Anthropic Economic Index and labor-market impacts",
        "source.anthropic.section": "observed occupation/task exposure and task penetration rows",
        "source.anthropic.note": (
            "Task rows are used only when local rows match the resolved O*NET-SOC code and exact O*NET task ID."
        ),
        "source.usage.title": "Anthropic Economic Index, release 2026-06-26 (Claude.ai, per occupation)",
        "source.usage.section": "soc_occupation rows for {month}, GLOBAL and TUR",
        "source.usage.note": "A missing Turkey value means Anthropic did not publish it (below its sample threshold).",
        "source.research.note": (
            "Claims matched by embedding similarity, then checked for relevance by an LLM (CHANGELOG 032)."
        ),
        "report.alternatives.header": "Alternatives at every preparation level",
        # The desktop layout (ROADMAP 10.2, 10.3).
        "report.tab.careers": "Careers",
        "report.list.department": "Your department's careers",
        "report.list.matches": "Your matches",
        "report.compare.level": "Preparation",
        "report.alternatives.caption": "The careers outside the list above that fit your interests best, three at each preparation level, from no degree to graduate school (O\\*NET's matching rule).",
        "report.department.all_weak": "None of your department's careers fits your interests: on O\\*NET's rule, every one fits your answers less than chance would. Your interests point to other kinds of work; see the alternatives below the list.",
        "report.detail.overview": "Overview",
        "report.detail.evidence": "AI evidence",
        "report.detail.skills": "Skills and education",
        "report.detail.steps": "Next steps",
        "report.ai.table.title": "Anthropic task coverage, task by task",
        "report.new_titles.header": "Newer job titles close to this career",
        "report.new_titles.note": "O\\*NET has no occupation equivalent to these titles, so we can only show their closest O\\*NET occupations; this career is one of them.",
        "report.new_titles.source.onet": "O\\*NET lists the title under this occupation.",
        "report.new_titles.source.adjusted": "O\\*NET lists the title under this occupation (its list was reviewed by hand).",
        "report.new_titles.source.proposed": "O\\*NET doesn't list the title; this occupation was chosen by hand as one of its closest.",
        "followup.optional_note": "Optional: a few open questions that can change the order of your careers. Your report is ready without them.",
        "report.alternatives.none": "No other career fits your interests at these preparation levels.",
        "report.sources.header": "Sources",
        "report.sources.expander": "View the sources",
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
        "app.method_references": "Yöntem kaynakları",
        "initial.instructions": (
            "Yapmak isteyeceğin etkinliklerin yanındaki kutuyu işaretle. Ne kadar eğitim/"
            "hazırlık gerektiğini veya ne kadar para kazanacağını düşünme."
        ),
        "initial.activities_header": "{count} İş Etkinliği",
        "initial.job_zone_header": "İş Bölgesi Soruları",
        "initial.current_job_zone_heading": "A. Mevcut İş Bölgesi",
        "initial.current_job_zone_question": (
            "Şu anda hangi eğitim, hazırlık ve deneyim düzeyine sahipsin?"
        ),
        "initial.future_job_zone_heading": "B. Hedeflenen İş Bölgesi",
        # The department question (ROADMAP 9.1).
        "initial.department_question": "Hangi bölümde okuyorsun?",
        "initial.department_placeholder": "Bölümünü seç",
        "initial.department_help": "Kariyerlerin bölümünden gelir ve yanıtlarına göre sıralanır. Bölümün listede yoksa son seçeneği seç; o zaman hazırlık düzeyi sorulur.",
        "initial.department_other": "Bölümüm listede yok",
        "profile.department": "Bölüm",
        "initial.future_job_zone_question": (
            "Hangi eğitim, hazırlık ve deneyim düzeyi için çalışmaya isteklisin?"
        ),
        "initial.submit": "Gönder",
        "followup.header": "Sıralamayı iyileştir (isteğe bağlı)",
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
        "artifacts.missing_title": "RAG dosyaları eksik. Lütfen kurulum/oluşturma komutunu çalıştır.",
        "artifacts.missing_list": "Eksik veya kullanılamayan dosyalar:",
        "artifacts.rebuild": "Ham/yerel kaynaklardan yeniden oluştur:",
        "artifacts.verify": "Ardından doğrula:",
        "report.summary.preferences": "Eşleştirmede Kullanılan Tercihler",
        "report.top_matches.caption": (
            "Bu rapor, mevcut İş Bölgen için en fazla beş kariyeri ve ulaşmaya istekli olduğun "
            "gelecek İş Bölgesi için en fazla beş kariyeri gösterir."
        ),
        "report.top_matches.caption_department": "Bunlar bölümünün kariyerleri; yanıtlarına ne kadar uyduklarına göre sıralandı.",
        "report.guidance.department": "Bu kariyerler bölümünden geliyor; yanıtlarına en çok uyanlar önce geliyor.",
        "report.top_matches.fit": "Uyum",
        "report.job.what_does": "Bu İş Ne Yapar",
        "report.job.no_description": "Yerel O*NET açıklaması getirilemedi.",
        "report.job.main_tasks": "Ana Görevler",
        "report.job.key_skills": "Temel Beceriler",
        "report.job.education_zone": "Eğitim / İş Bölgesi",
        "report.job.ai_impact": "Yapay Zekâ Etkisi Dağılımı",
        "report.job.day_life": "Günlük İş Akışı",
        "report.ai.caption": (
            "Görev kapsamı, Anthropic'in işgücü piyasası etkileri verisinden gelir (Ağustos ve Kasım "
            "2025 Claude kullanımı). Bir görev, işle ilgili yeterli Claude kullanımı olduğunda ve dil "
            "modellerinin yapabileceği bir görev olduğunda kapsanmış sayılır. \"Çoğunlukla otomasyon\", "
            "görevi çoğunlukla Claude'un yaptığı; \"çoğunlukla destekleme\", insanların görevi çoğunlukla "
            "Claude ile birlikte yaptığı anlamına gelir. Kapsanıyor olması mesleğin ortadan kalkacağı "
            "anlamına gelmez. "
            "Kapsanmıyor olması da görevin yapay zekâdan etkilenmeyeceği anlamına gelmez: yalnızca bu "
            "Claude verisinde görülmediğini gösterir; başka yapay zekâ araçları, robotlar veya gelecekteki "
            "modeller hakkında bir şey söylemez. "
            "Veri yok, Anthropic'in bu O*NET görevi için satırı olmadığı anlamına gelir; bu kapsanmıyor "
            "ile aynı şey değildir."
        ),
        "report.ai.no_rows": "Bu meslek için yapay zekâ etkisi satırı bulunamadı.",
        # About the data, said once (ROADMAP 9.5).
        "app.caption": (
            "Üniversite öğrencileri için bir kariyer rehberi: bölümüne ve ilgi alanlarına göre kariyerler önerir "
            "ve her iş için yapay zekâ hakkında kanıtların ne söylediğini gösterir; kanıt olmadığında bunu da "
            "söyler."
        ),
        "report.tab.about": "Veriler hakkında",
        "about.careers.title": "Kariyerler nereden geliyor",
        "about.careers.text": (
            "Bölümünün kariyerleri, bölümünün karşılık geldiği ABD öğrenim alanlarından, ABD eğitim "
            "istatistikleri kurumunun (NCES) resmî öğrenim alanı ile meslek eşleştirmesi üzerinden geliyor ve "
            "elle gözden geçirildi. Bölüm seçmezsen, seçtiğin hazırlık düzeylerindeki tüm mesleklere O\\*NET'in "
            "kendi eşleştirme kuralı uygulanır. Her iki durumda da kariyerler, ilgi puanlarının her kariyerinkine "
            "ne kadar uyduğuna göre sıralanır (O\\*NET'in Interest Profiler kuralı). Alternatifler, aynı kurala göre "
            "listenin dışında her hazırlık düzeyinde en iyi uyanlardır. Kariyerler ve tanımları "
            "O\\*NET'ten gelir; O\\*NET ABD'deki işleri anlatır."
        ),
        "about.picture.title": "Yapay zekâ tablosu",
        "about.picture.text": (
            "Her kariyerin yapay zekâ tablosu iki kaynağı karşılaştırır ve hiçbir zaman ortalamasını almaz: ana "
            "görevlerinden kaçı için insanların Claude'u zaten kullandığı ve uzmanların bu tür işi ne kadar açık "
            "değerlendirdiği (ILO). Kaynaklar uyuştuğunda bunu söyler; çeliştiğinde bunu da söyler."
        ),
        "about.anthropic.title": "Claude kullanımı (Anthropic)",
        "about.anthropic.estimates": (
            "İnsanların bir iş için Claude'u ne kadar kullandığı kullanımı gösterir; kaç işin değiştiğini değil. "
            "Anthropic'in süre tahminleri, konuşmaları okuyan bir modelden gelir; ölçülmüş verimlilik değildir."
        ),
        "about.ilo.title": "Uzman değerlendirmesi (ILO)",
        "about.ilo.text": (
            "Uluslararası Çalışma Örgütü (ILO), her meslek grubunun görevlerini üretken yapay zekâya olası "
            "maruziyetlerine göre anketler, uzmanlar ve bir modelle değerlendirir. Bu gözlemlenen kullanım değil "
            "bir değerlendirmedir; bu yüzden Claude verisinden farklı olabilir ve tek bir kariyerden daha geniş "
            "bir meslek grubunu anlatır."
        ),
        "about.research.title": "Araştırma bulguları",
        "about.next.title": "Sonraki adımlar",
        "about.next.text": (
            "Her kariyerin sonraki adımları, kendi verisinden tek bir kuralla çıkar. Önce ABD iş ilanlarının "
            "aradığı araçları (O\\*NET'in talep gören yazılımları); en az başka meslekte arananlar önce gelir, "
            "Excel gibi genel ofis yazılımları dışarıda bırakılır. Bu araçları olmayan bir kariyer için en çok "
            "dayandığı iki bilgi alanı gösterilir. Sonra, insanlar ana görevlerinden biri için Claude'u zaten "
            "kullanıyorsa o görev. Son olarak, staj ya da ders projesinde denemek için en önemli diğer görevi."
        ),
        # The AI snapshot on each career (ROADMAP 9.2).
        "snapshot.chip": "YZ kullanımı görülen görev: {seen}/{total}",
        "snapshot.chip_none": "YZ görev verisi yok",
        "snapshot.claude.seen": "Bu işin {total} ana görevinden {seen} tanesi için Claude kullanımı görüldü (Anthropic, 2025).",
        "snapshot.claude.zero": "Bu işin {total} ana görevinin hiçbiri için Claude kullanımı görülmedi (Anthropic, 2025).",
        "snapshot.claude.none": "Bu iş için Claude görev verisi yok.",
        "snapshot.ilo.high": "Uzmanlar bu tür işi üretken yapay zekâya yüksek düzeyde açık değerlendiriyor (ILO).",
        "snapshot.ilo.medium": "Uzmanlar bu tür işi üretken yapay zekâya orta düzeyde açık değerlendiriyor (ILO).",
        "snapshot.ilo.low": "Uzmanlar bu tür işi üretken yapay zekâya az açık değerlendiriyor (ILO).",
        "snapshot.ilo.none": "Bu tür iş için uzman değerlendirmesi yok.",
        "snapshot.research.many": "Bu kariyerle ilgili {count} araştırma bulgusu ayrıntılarda.",
        "snapshot.research.one": "Bu kariyerle ilgili bir araştırma bulgusu ayrıntılarda.",
        "snapshot.research.none": "Koleksiyonumuzdaki hiçbir çalışma henüz bu kariyere özgü değil.",
        "snapshot.verdict.high_reach": "Yapay zekâ bu işin büyük kısmına şimdiden ulaşıyor: görevlerinin değişmesini bekle.",
        "snapshot.verdict.low_reach": "Kaynaklar yapay zekânın bu işe şimdilik pek ulaşmadığını gösteriyor; bu, yapay zekâdan güvende olduğu anlamına gelmez.",
        "snapshot.verdict.disagree_unseen": "Kaynaklar çelişiyor: bu görevler için Claude kullanımı görülmedi, ama uzmanlar işi yapay zekâya açık değerlendiriyor. Görülmemesi güvende olduğu anlamına gelmez.",
        "snapshot.verdict.disagree_used": "Kaynaklar çelişiyor: insanlar bu görevlerin çoğu için Claude'u zaten kullanıyor, ama uzmanlar işi daha az açık değerlendiriyor.",
        "snapshot.verdict.partial": "Yapay zekâ bu işin bir kısmına ulaşıyor, tamamına değil.",
        "snapshot.verdict.none": "Kaynaklarımızda bu iş için yapay zekâ verisi yok.",
        # The comparison table (ROADMAP 9.3).
        "report.compare.career": "Kariyer",
        "report.compare.fit": "Uyum",
        "report.compare.picture": "YZ tablosu",
        "snapshot.short.high_reach": "YZ çok ulaşıyor",
        "snapshot.short.low_reach": "şimdilik az",
        "snapshot.short.disagree_unseen": "kaynaklar çelişiyor",
        "snapshot.short.disagree_used": "kaynaklar çelişiyor",
        "snapshot.short.partial": "kısmen",
        "snapshot.short.none": "veri yok",
        "report.usage.title": "İnsanlar bu iş için Claude'u nasıl kullanıyor ({month})",
        "report.usage.share": "Dünya genelindeki tüm Claude.ai konuşmalarında bu mesleğin görevlerinin payı: {global_pct}.",
        "report.usage.share_turkey": "Türkiye'de: {turkey_pct}.",
        "report.usage.share_turkey_missing": "Türkiye: yayımlanmadı (konuşma sayısı Anthropic'in eşiğinin altında).",
        "report.usage.split": (
            "Otomasyon tarzı (görevi Claude yürütüyor): {automation_pct}; "
            "destekleme tarzı (kişi görevi Claude ile birlikte yürütüyor): {augmentation_pct}."
        ),
        "report.usage.time": "Anthropic'in tahmini: bir kişi tek başına yaklaşık {hours} saat, yapay zekâ ile yaklaşık {minutes} dakika.",
        "report.usage.below": "{value} altında",
        "report.ilo.title": "Bu tür işin üretken yapay zekâya maruziyeti (ILO)",
        "report.ilo.scope": (
            "Bu, ILO'nun daha geniş ISCO-08 grubu {code} \"{title}\" için verdiği puandır; bu grup, bu uygulamadaki "
            "{others} başka kariyeri de kapsar."
        ),
        "report.ilo.scope_single": "Bu, ILO'nun ISCO-08 grubu {code} \"{title}\" için verdiği puandır.",
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
            "Koleksiyonumuzdaki yapay zekâ ve iş konulu rapor ve makalelerden alınan bulgular; her mesleğe benzerlikle "
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
        "report.why.interests_shared": "En güçlü iki ilgi alanı ({career}) senin alanlarının arasında ({student}). {marker}",
        "report.why.interests_one": "En güçlü iki ilgi alanından ({career}) {shared} senin alanlarından biri ({student}). {marker}",
        "report.why.interests_other": (
            "En güçlü ilgi alanları ({career}) senin ilk üç alanın ({student}) arasında değil; "
            "bu yüzden yanıtlarına daha az uyuyor. {marker}"
        ),
        "report.why.activities": "Bu işe uyan ve evet dediğin etkinlikler: {activities}.",
        "report.why.department": "Bölümünün yol açtığı kariyerlerden biri.",
        "report.guidance.default": (
            "Hedeflediğin öneriler için gelecek İş Bölgesine, hemen başlayabileceğin seçenekler için mevcut İş "
            "Bölgene bak."
        ),
        "report.guidance.followup": (
            "Adaylar, O*NET Interest Profiler'ın ilk eşleşmeleridir; takip sorularına verdiğin yanıtlara ve "
            "O*NET meslek bilgilerine göre yeniden sıralandılar."
        ),
        "report.resolution_note": "{display_title} olarak gösteriliyor; O*NET verisi {resolved_title} mesleğinden alındı.",
        # The card test and profile screens (moved from interest_profiler_app.py, ROADMAP 7.1).
        "hero.status": "İlgi profili",
        "results.header": "Sonuçların",
        # Next steps per career, by a stated rule (ROADMAP 9.7).
        "report.next.tools": "Bu meslek için iş ilanlarının aradığı araçları öğren: {tools} (O*NET).",
        "report.next.knowledge": "Bu işin en çok dayandığı bilgi alanlarını geliştir: {areas} (O*NET).",
        "report.next.ai": "İnsanlar “{task}” için Claude'u zaten kullanıyor: bunu bir yapay zekâ aracıyla dene ve hatalarını yakalamayı öğren.",
        "report.next.try": "Seçmeden önce işi dene: “{task}” görevini içeren bir staj ya da ders projesi ara.",
        "results.change_answers": "Cevaplarımı değiştir",
        "results.back": "Sonuçlarıma dön",
        "assessment.header": "Hızlı kartlarla başla",
        "assessment.test": "Test uzunluğu",
        "assessment.test.mini_ip_30": "Hızlı: 30 etkinlik",
        "assessment.test.short_form_60": "Tam: 60 etkinlik",
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
        "profile.code": "Kariyer kodu",
        "profile.current_zone": "Mevcut bölge",
        "profile.future_zone": "Hedef bölge",
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
        "source.onet.note": "O*NET-SOC {code}",
        "source.anthropic.title": "Anthropic Economic Index ve işgücü piyasası etkileri",
        "source.anthropic.section": "meslek ve görev düzeyinde gözlemlenen maruziyet ve görev kapsamı verileri",
        "source.anthropic.note": (
            "Görev verileri yalnızca eşleştirilen O*NET-SOC koduna ve birebir O*NET görev numarasına uyduğunda "
            "kullanılır."
        ),
        "source.usage.title": "Anthropic Economic Index, 2026-06-26 sürümü (Claude.ai, meslek bazında)",
        "source.usage.section": "{month} için soc_occupation satırları, GLOBAL ve TUR",
        "source.usage.note": "Türkiye değeri yoksa Anthropic onu yayımlamamıştır (örneklem eşiğinin altında).",
        "source.research.note": (
            "Bulgular anlam benzerliğiyle eşleştirildi, ardından bir dil modeliyle ilgililik açısından kontrol "
            "edildi (CHANGELOG 032)."
        ),
        "report.alternatives.header": "Her hazırlık düzeyinde alternatifler",
        # The desktop layout (ROADMAP 10.2, 10.3).
        "report.tab.careers": "Kariyerler",
        "report.list.department": "Bölümünün kariyerleri",
        "report.list.matches": "Eşleşmelerin",
        "report.compare.level": "Hazırlık",
        "report.alternatives.caption": "Yukarıdaki listenin dışında ilgi alanlarına en iyi uyan kariyerler; diplomasız işlerden lisansüstüne, her hazırlık düzeyinde üçer tane (O\\*NET'in eşleştirme kuralı).",
        "report.department.all_weak": "Bölümünün kariyerlerinden hiçbiri ilgi alanlarına uymuyor: O\\*NET'in kuralına göre her biri cevaplarına rastlantıdan daha az uyuyor. İlgi alanların başka türden işlere işaret ediyor; listenin altındaki alternatiflere bak.",
        "report.detail.overview": "Genel bakış",
        "report.detail.evidence": "Yapay zekâ kanıtı",
        "report.detail.skills": "Beceriler ve eğitim",
        "report.detail.steps": "Sonraki adımlar",
        "report.ai.table.title": "Görev görev Anthropic görev kapsamı",
        "report.new_titles.header": "Bu kariyere yakın yeni meslek unvanları",
        "report.new_titles.note": "O\\*NET'te bu unvanlara karşılık gelen bir meslek yok; bu yüzden yalnızca onlara en yakın O\\*NET mesleklerini gösterebiliyoruz ve bu kariyer onlardan biri.",
        "report.new_titles.source.onet": "O\\*NET bu unvanı bu mesleğin altında listeliyor.",
        "report.new_titles.source.adjusted": "O\\*NET bu unvanı bu mesleğin altında listeliyor (liste elle gözden geçirildi).",
        "report.new_titles.source.proposed": "O\\*NET bu unvanı listelemiyor; bu meslek, ona en yakınlardan biri olarak elle seçildi.",
        "followup.optional_note": "İsteğe bağlı: kariyerlerinin sırasını değiştirebilecek birkaç açık uçlu soru. Raporun bunlar olmadan da hazır.",
        "report.alternatives.none": "Bu hazırlık düzeylerinde ilgi alanlarına uyan başka bir kariyer yok.",
        "report.sources.header": "Kaynaklar",
        "report.sources.expander": "Kaynakları görüntüle",
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
        "Careers from your department": "Bölümünden kariyerler",
        "Best fit": "En iyi uyum",
        "Great fit": "Çok iyi uyum",
        "Good fit": "İyi uyum",
        "Weak fit": "Zayıf uyum",
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
    """The ILO panel's sentences (D5 = B): the exposure group and its meaning, and the group it belongs to.
    No combined score with the Claude data; what the rating is, is explained once under About the data (9.5)."""
    language = normalize_language(language)
    name, meaning = ILO_GRADIENTS[language][ilo["gradient"]]
    title = content_text(ilo["isco08_title"], language)
    others = ilo["careers_in_group"] - 1
    scope = (ui_text("report.ilo.scope", language, code=ilo["isco08_code"], title=title, others=others) if others
             else ui_text("report.ilo.scope_single", language, code=ilo["isco08_code"], title=title))
    return [f"{name}: {meaning}.", scope]


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
