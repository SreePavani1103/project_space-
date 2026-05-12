/* =========================================================
   SKILL SYNTH AI — report.js  (Full 11-Section Dashboard)
   ========================================================= */

(function () {
    "use strict";

    const reportPage = document.querySelector(".report-page");
    if (!reportPage) return;

    const reportId = reportPage.dataset.reportId;
    const contentEl = document.getElementById("reportContent");

    // ── Helpers ──────────────────────────────────────────────
    function animateRing(id, pct, circumference = 327) {
        const el = document.getElementById(id);
        if (!el) return;
        const dashLen = (pct / 100) * circumference;
        setTimeout(() => {
            el.style.transition = "stroke-dasharray 1.5s cubic-bezier(0.16, 1, 0.3, 1)";
            el.setAttribute("stroke-dasharray", `${dashLen}, ${circumference}`);
        }, 300);
    }

    function safe(val, fallback = "—") {
        return (val !== null && val !== undefined && val !== "") ? val : fallback;
    }

    function renderSection(title, icon, content, id = "") {
        return `<div class="report-section glass" ${id ? `id="${id}"` : ""}>
            <h2 class="report-section__title"><span>${icon}</span> ${title}</h2>
            <div class="report-section__body">${content}</div>
        </div>`;
    }

    function chip(text, cls = "") {
        return `<span class="chip ${cls}">${text}</span>`;
    }

    function chipList(items, cls = "") {
        if (!items?.length) return `<p class="text-muted">None detected.</p>`;
        return `<div class="chip-wrap">${items.map(s => {
            const name = typeof s === "object" ? s.skill || s.name || s : s;
            return chip(name, cls);
        }).join("")}</div>`;
    }

    function renderResourceCard(item, icon = "🔗") {
        const title = item.title || item.name || "Resource";
        const url = item.url || "#";
        const desc = item.description || item.skill || item.why || item.why_study || "";
        const badge = item.free === true ? `<span class="chip chip--green" style="font-size:10px">FREE</span>` :
                      item.free === false ? `<span class="chip chip--amber" style="font-size:10px">PAID</span>` : "";
        return `<a href="${url}" target="_blank" rel="noopener" class="resource-item glass">
            <span class="resource-icon">${icon}</span>
            <div class="resource-body">
                <strong>${title}</strong>${badge}
                ${desc ? `<p>${desc}</p>` : ""}
            </div>
            <span class="resource-arrow">↗</span>
        </a>`;
    }

    // ── Section Renderers ─────────────────────────────────────

    // 1. Overall Assessment
    function renderAssessment(ai) {
        if (!ai.overall_assessment) return "";
        return renderSection("Overall Assessment", "🎯",
            `<p class="assessment-text">${ai.overall_assessment}</p>
             ${ai.time_to_ready ? `<p class="time-ready"><strong>⏱ Estimated time to job-ready:</strong> ${ai.time_to_ready}</p>` : ""}`,
            "sec-assessment"
        );
    }

    // 2. Skill Gap Summary (categorized table)
    function renderSkillGapSummary(ai) {
        const sgap = ai.skill_gap_summary;
        if (!sgap) {
            // Fallback to flat lists
            return renderSection("Skill Analysis", "◈",
                `<div class="skills-grid">
                    <div class="skills-col"><h4 class="text-green">✅ Strong</h4>${chipList(ai.strong_skills, "chip--green")}</div>
                    <div class="skills-col"><h4 class="text-amber">⚠️ Weak</h4>${chipList(ai.weak_skills, "chip--amber")}</div>
                    <div class="skills-col"><h4 class="text-red">❌ Missing</h4>${chipList(ai.missing_skills, "chip--red")}</div>
                </div>`, "sec-skills"
            );
        }

        const statusIcon = s => s === "strong" ? "✅" : s === "weak" ? "⚠️" : "❌";
        const statusCls  = s => s === "strong" ? "chip--green" : s === "weak" ? "chip--amber" : "chip--red";
        const priCls     = p => p === "high" ? "chip--red" : p === "medium" ? "chip--amber" : "chip--cyan";

        const categories = [
            { key: "programming_languages", label: "Programming Languages", icon: "💻" },
            { key: "frameworks_libraries",  label: "Frameworks & Libraries", icon: "📦" },
            { key: "dsa_problem_solving",   label: "DSA / Problem Solving",  icon: "🧩" },
            { key: "system_design",         label: "System Design",           icon: "🏗️" },
            { key: "tools_devops",          label: "Tools & DevOps",          icon: "⚙️" },
        ];

        let tableHtml = `<div class="skill-gap-categories">`;
        categories.forEach(cat => {
            const items = sgap[cat.key] || [];
            if (!items.length) return;
            tableHtml += `<div class="sgap-category glass">
                <h4>${cat.icon} ${cat.label}</h4>
                <table class="sgap-table">
                    <thead><tr><th>Skill</th><th>Status</th><th>Priority</th></tr></thead>
                    <tbody>${items.map(i => `<tr>
                        <td>${i.skill}</td>
                        <td>${chip(statusIcon(i.status) + " " + i.status, statusCls(i.status))}</td>
                        <td>${chip(i.priority, priCls(i.priority))}</td>
                    </tr>`).join("")}</tbody>
                </table>
            </div>`;
        });
        tableHtml += `</div>`;

        // Also show strong/weak/missing as chips below
        tableHtml += `<div class="skills-grid" style="margin-top:20px">
            <div class="skills-col"><h4 class="text-green">✅ Strong Skills</h4>${chipList(ai.strong_skills, "chip--green")}</div>
            <div class="skills-col"><h4 class="text-amber">⚠️ Weak Skills</h4>${chipList(ai.weak_skills, "chip--amber")}</div>
            <div class="skills-col"><h4 class="text-red">❌ Missing Skills</h4>${chipList(ai.missing_skills, "chip--red")}</div>
        </div>`;

        return renderSection("Skill Analysis", "◈", tableHtml, "sec-skills");
    }

    // 3. Coding Questions to Practice
    function renderCodingQuestions(ai) {
        const items = ai.coding_questions_to_practice;
        if (!items?.length) return "";
        const diffCls = d => d === "easy" ? "chip--green" : d === "hard" ? "chip--red" : "chip--amber";
        let html = `<div class="coding-topics">`;
        items.forEach(topic => {
            const questions = topic.questions || [];
            html += `<div class="coding-topic glass">
                <h4>${topic.topic || ""} ${chip(topic.difficulty || "", diffCls(topic.difficulty))}</h4>
                <ul class="question-list">`;
            questions.forEach(q => {
                if (typeof q === "object") {
                    const platIcon = q.platform === "LeetCode" ? "🟡" : q.platform === "HackerRank" ? "🟢" : "🔵";
                    html += `<li><a href="${q.url || "#"}" target="_blank" rel="noopener">${platIcon} ${q.title}</a>${q.why ? `<span class="q-why"> — ${q.why}</span>` : ""}</li>`;
                } else {
                    html += `<li>${q}</li>`;
                }
            });
            html += `</ul></div>`;
        });
        html += `</div>`;
        return renderSection("Coding Questions to Practice", "⌨️", html, "sec-coding");
    }

    // 4. DSA Sheets
    function renderDSASheets(resources) {
        const sheets = resources?.dsa_sheets;
        if (!sheets?.length) return "";
        let html = `<div class="dsa-sheets-grid">`;
        sheets.forEach(s => {
            html += `<a href="${s.url || "#"}" target="_blank" rel="noopener" class="dsa-card glass">
                <div class="dsa-card__header">
                    <strong>${s.name || "Sheet"}</strong>
                    <span class="chip chip--cyan">${s.problems_count || ""} problems</span>
                </div>
                <p>${s.description || ""}</p>
                <span class="resource-arrow">Start →</span>
            </a>`;
        });
        html += `</div>`;
        return renderSection("DSA Sheets", "📋", html, "sec-dsa-sheets");
    }

    // 5. Courses
    function renderCourses(resources) {
        const items = resources?.courses;
        if (!items?.length) return "";
        return renderSection("Courses", "🎓",
            `<div class="resource-list">${items.map(c => renderResourceCard(c, "🎓")).join("")}</div>`,
            "sec-courses"
        );
    }

    // 6. Articles & Docs
    function renderArticles(resources) {
        const items = resources?.articles_and_docs;
        if (!items?.length) return "";
        return renderSection("Articles & Documentation", "📄",
            `<div class="resource-list">${items.map(a => renderResourceCard(a, "📄")).join("")}</div>`,
            "sec-articles"
        );
    }

    // 7. GitHub Repos to Study
    function renderGitHubRepos(resources) {
        const items = resources?.github_repositories;
        if (!items?.length) return "";
        let html = `<div class="resource-list">${items.map(r => {
            const starsText = r.stars ? `⭐ ${r.stars}` : "";
            return `<a href="${r.url || "#"}" target="_blank" rel="noopener" class="resource-item glass">
                <span class="resource-icon">📂</span>
                <div class="resource-body">
                    <strong>${r.name || "Repo"}</strong> ${starsText ? `<span class="chip chip--cyan" style="font-size:10px">${starsText}</span>` : ""}
                    <p>${r.description || ""}</p>
                    ${r.why_study ? `<p class="text-muted" style="font-size:12px">📌 ${r.why_study}</p>` : ""}
                </div>
                <span class="resource-arrow">↗</span>
            </a>`;
        }).join("")}</div>`;
        return renderSection("GitHub Repositories to Study", "📂", html, "sec-gh-repos");
    }

    // 8. Personalized Resources (YouTube)
    function renderYoutube(resources) {
        const items = resources?.youtube_playlists;
        if (!items?.length) return "";
        let html = `<div class="resource-list">${items.map(v => {
            return `<a href="${v.url || "#"}" target="_blank" rel="noopener" class="resource-item glass">
                <span class="resource-icon">📺</span>
                <div class="resource-body">
                    <strong>${v.title || "Playlist"}</strong>
                    ${v.channel ? `<span class="chip chip--purple" style="font-size:10px">${v.channel}</span>` : ""}
                    ${v.duration ? `<span class="chip" style="font-size:10px">⏱ ${v.duration}</span>` : ""}
                    <p>${v.description || v.skill || ""}</p>
                </div>
                <span class="resource-arrow">▶</span>
            </a>`;
        }).join("")}</div>`;
        return renderSection("Personalized Resources (YouTube)", "📺", html, "sec-youtube");
    }

    // 9. Recommended Projects
    function renderProjects(ai) {
        const items = ai.recommended_projects;
        if (!items?.length) return "";
        const diffCls = d => d === "beginner" ? "chip--green" : d === "advanced" ? "chip--red" : "chip--amber";
        let html = `<div class="projects-grid">`;
        items.forEach(p => {
            const features = p.key_features || p.skills_practiced || [];
            const skills = p.skills_gained || p.skills_practiced || [];
            html += `<div class="project-card glass">
                <div class="project-header">
                    <h4>${p.title || "Project"}</h4>
                    ${chip(p.difficulty || "intermediate", diffCls(p.difficulty))}
                    ${p.estimated_time ? `<span class="chip" style="font-size:10px">⏱ ${p.estimated_time}</span>` : ""}
                </div>
                <p>${p.description || ""}</p>
                ${skills.length ? `<div style="margin-top:8px"><strong>Skills Gained:</strong><div class="chip-wrap" style="margin-top:4px">${skills.map(s => chip(s, "chip--cyan")).join("")}</div></div>` : ""}
                ${features.length ? `<div style="margin-top:10px"><strong>Key Features:</strong><ul style="margin:4px 0 0 16px">${features.map(f => `<li>${f}</li>`).join("")}</ul></div>` : ""}
            </div>`;
        });
        html += `</div>`;
        return renderSection("Recommended Projects", "💡", html, "sec-projects");
    }

    // 10. Improvement Roadmap (30/60/90 day)
    function renderRoadmap(ai) {
        const roadmap = ai.improvement_roadmap;
        if (!roadmap) return "";

        // New structured 30/60/90 day format
        if (roadmap.day_30) {
            const days = [
                { key: "day_30", label: "30-Day Plan", icon: "🚀", color: "var(--accent-cyan)" },
                { key: "day_60", label: "60-Day Plan", icon: "📈", color: "var(--accent-amber)" },
                { key: "day_90", label: "90-Day Plan", icon: "🏆", color: "var(--accent-purple)" },
            ];
            let html = `<div class="roadmap-days">`;
            days.forEach(d => {
                const plan = roadmap[d.key] || {};
                html += `<div class="roadmap-day glass" style="border-top: 3px solid ${d.color}">
                    <h4>${d.icon} ${d.label}</h4>
                    ${plan.goal ? `<p class="roadmap-goal"><strong>Goal:</strong> ${plan.goal}</p>` : ""}
                    ${plan.skills_to_cover?.length ? `<div class="chip-wrap">${plan.skills_to_cover.map(s => chip(s, "chip--cyan")).join("")}</div>` : ""}
                    ${plan.tasks?.length ? `<ul class="phase-tasks">${plan.tasks.map(t => `<li>${t}</li>`).join("")}</ul>` : ""}
                </div>`;
            });
            html += `</div>`;
            return renderSection("Improvement Roadmap", "🗺️", html, "sec-roadmap");
        }

        // Legacy phase format fallback
        if (Array.isArray(roadmap) && roadmap.length) {
            let html = `<div class="roadmap-timeline">`;
            roadmap.forEach(phase => {
                html += `<div class="roadmap-phase glass">
                    <div class="phase-header">
                        <span class="phase-num">Phase ${phase.phase || ""}</span>
                        <strong>${phase.title || ""}</strong>
                        <span class="phase-duration">${phase.duration || ""}</span>
                    </div>
                    <ul class="phase-tasks">${(phase.tasks || []).map(t => `<li>${t}</li>`).join("")}</ul>
                    ${phase.skills_covered?.length ? `<div class="chip-wrap">${phase.skills_covered.map(s => chip(s, "chip--cyan")).join("")}</div>` : ""}
                </div>`;
            });
            html += `</div>`;
            return renderSection("Improvement Roadmap", "🗺️", html, "sec-roadmap");
        }
        return "";
    }

    // 11a. LeetCode / DSA Analysis
    function renderLeetCode(leetcode, ai) {
        if (!leetcode || leetcode.error || !leetcode.total_solved) return "";
        const weekly = ai?.weekly_leetcode_plan;

        let html = `<div class="github-summary">
            <div class="gh-stat"><strong>${safe(leetcode.total_solved)}</strong><span>Total Solved</span></div>
            <div class="gh-stat text-green"><strong>${safe(leetcode.easy_solved, 0)}</strong><span>Easy</span></div>
            <div class="gh-stat text-amber"><strong>${safe(leetcode.medium_solved, 0)}</strong><span>Medium</span></div>
            <div class="gh-stat text-red"><strong>${safe(leetcode.hard_solved, 0)}</strong><span>Hard</span></div>
        </div>
        <div class="chart-wrap"><canvas id="lcChart" height="200"></canvas></div>`;

        if (leetcode.contest_rating) {
            html += `<p style="margin-top:12px"><strong>Contest Rating:</strong> ${leetcode.contest_rating}</p>`;
        }
        if (leetcode.strong_topics?.length) {
            html += `<div style="margin-top:12px"><h4>✅ Strong Topics</h4><div class="chip-wrap">${leetcode.strong_topics.map(t => chip(t, "chip--green")).join("")}</div></div>`;
        }
        if (leetcode.weak_topics?.length) {
            html += `<div style="margin-top:12px"><h4>⚠️ Weak Topics</h4><div class="chip-wrap">${leetcode.weak_topics.map(t => chip(t, "chip--red")).join("")}</div></div>`;
        }

        // Weekly plan
        if (weekly?.length) {
            html += `<div style="margin-top:20px"><h4>📅 Suggested Weekly Practice Plan</h4><div class="weekly-plan">`;
            weekly.forEach(w => {
                html += `<div class="week-card glass">
                    <span class="chip chip--purple">Week ${w.week}</span>
                    <strong>${w.focus || ""}</strong>
                    <p>${w.difficulty_mix || ""} · ${w.target_problems || ""} problems</p>
                    ${w.topics?.length ? `<div class="chip-wrap">${w.topics.map(t => chip(t)).join("")}</div>` : ""}
                </div>`;
            });
            html += `</div></div>`;
        }

        return renderSection("LeetCode / DSA Analysis", "⊹", html, "sec-leetcode");
    }

    // 11b. GitHub Analysis + Improvements
    function renderGitHub(github, ai) {
        if (!github || github.error) return "";

        const profile = github.profile || {};
        const langs = github.languages || {};
        const langLabels = Object.keys(langs).slice(0, 8);
        const langValues = langLabels.map(l => langs[l]);

        let html = `<div class="github-summary">
            <div class="gh-stat"><strong>${safe(github.total_repos, 0)}</strong><span>Repos</span></div>
            <div class="gh-stat"><strong>${safe(github.total_stars, 0)}</strong><span>Stars</span></div>
            <div class="gh-stat"><strong>${safe(github.commit_consistency, "N/A")}</strong><span>Consistency</span></div>
            <div class="gh-stat"><strong>${github.ai_ml_usage ? "Yes" : "No"}</strong><span>AI/ML Work</span></div>
        </div>`;

        if (langLabels.length) {
            html += `<div class="chart-wrap"><canvas id="langChart" height="200"></canvas></div>`;
        }
        if (github.frameworks?.length) {
            html += `<div style="margin-top:16px"><h4>Frameworks Detected</h4><div class="chip-wrap">${github.frameworks.map(f => chip(f, "chip--cyan")).join("")}</div></div>`;
        }

        // GitHub improvement suggestions
        const imp = ai?.github_improvements;
        if (imp) {
            html += `<div class="github-improvements" style="margin-top:24px">
                <h4>💡 How to Improve Your GitHub Profile</h4>
                <div class="improvement-grid">`;
            if (imp.project_types_to_add?.length) {
                html += `<div class="imp-card glass"><h5>📁 Projects to Add</h5><ul>${imp.project_types_to_add.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
            }
            if (imp.readme_tips?.length) {
                html += `<div class="imp-card glass"><h5>📝 README Tips</h5><ul>${imp.readme_tips.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
            }
            if (imp.contribution_ideas?.length) {
                html += `<div class="imp-card glass"><h5>🤝 Contribution Ideas</h5><ul>${imp.contribution_ideas.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
            }
            if (imp.profile_tips?.length) {
                html += `<div class="imp-card glass"><h5>👤 Profile Tips</h5><ul>${imp.profile_tips.map(i => `<li>${i}</li>`).join("")}</ul></div>`;
            }
            html += `</div></div>`;
        }

        return renderSection("GitHub Analysis", "⌬", html, "sec-github");
    }

    // ── Main load ─────────────────────────────────────────────
    async function loadReport() {
        try {
            const resp = await fetch(`/api/report/${reportId}`);
            const json = await resp.json();
            if (json.error) throw new Error(json.error);

            const data     = json.data || {};
            const ai       = data.ai_report || {};
            const summary  = data.summary || {};
            const github   = data.github_analysis || {};
            const leetcode = data.leetcode_analysis || {};
            const resources= data.resources || {};
            const skillGap = data.skill_gap || {};

            // Animate score rings
            animateRing("readinessRing", summary.hiring_readiness || 0);
            animateRing("atsRing", summary.ats_score || 0);
            animateRing("ghRing", summary.github_score || 0);

            // Build the full dashboard in order
            let html = "";
            html += renderAssessment(ai);
            html += renderSkillGapSummary(ai);
            html += renderCodingQuestions(ai);
            html += renderDSASheets(resources);
            html += renderCourses(resources);
            html += renderArticles(resources);
            html += renderGitHubRepos(resources);
            html += renderYoutube(resources);
            html += renderProjects(ai);
            html += renderRoadmap(ai);
            html += renderLeetCode(leetcode, ai);
            html += renderGitHub(github, ai);

            if (!html) {
                html = `<div class="report-section glass"><p class="text-muted" style="padding:40px;text-align:center;">
                    No report data available. Please run a new analysis.</p></div>`;
            }

            contentEl.innerHTML = html;

            // ── Charts (after DOM paint) ──────────────────────
            setTimeout(() => {
                // Language doughnut chart
                const langCtx = document.getElementById("langChart");
                if (langCtx && window.Chart) {
                    const langs = github.languages || {};
                    const labels = Object.keys(langs).slice(0, 8);
                    const values = labels.map(l => langs[l]);
                    new Chart(langCtx, {
                        type: "doughnut",
                        data: {
                            labels,
                            datasets: [{ data: values, backgroundColor: ["#7df9ff","#f5b66c","#ff7fa3","#8bf2c5","#b4a0ff","#ffd166","#06d6a0","#118ab2"], borderWidth: 0 }],
                        },
                        options: { responsive: true, plugins: { legend: { position: "right", labels: { color: "#d4d7e3", font: { family: "'Geist', sans-serif", size: 12 } } } }, cutout: "60%" },
                    });
                }

                // LeetCode bar chart
                const lcCtx = document.getElementById("lcChart");
                if (lcCtx && window.Chart) {
                    new Chart(lcCtx, {
                        type: "bar",
                        data: {
                            labels: ["Easy", "Medium", "Hard"],
                            datasets: [{ data: [leetcode.easy_solved || 0, leetcode.medium_solved || 0, leetcode.hard_solved || 0], backgroundColor: ["#8bf2c5","#f5b66c","#ff7fa3"], borderRadius: 8, barThickness: 40 }],
                        },
                        options: { responsive: true, plugins: { legend: { display: false } }, scales: { x: { ticks: { color: "#d4d7e3" }, grid: { display: false } }, y: { ticks: { color: "#8b8e9c" }, grid: { color: "rgba(255,255,255,0.05)" } } } },
                    });
                }
            }, 100);

        } catch (err) {
            contentEl.innerHTML = `<div class="report-section glass"><h2>Error Loading Report</h2><p>${err.message}</p></div>`;
        }
    }

    loadReport();
})();
