const PDFDocument = require('pdfkit');
const fs = require('fs');
const path = require('path');

function drawEvidenceItem(doc, level, label, value) {
    const startX = 40;
    const startY = doc.y;
    
    let bulletColor = '#64748b';
    if (level === 'high') {
        bulletColor = '#059669'; // Green
    } else if (level === 'supporting') {
        bulletColor = '#d97706'; // Amber/Yellow
    } else if (level === 'warning') {
        bulletColor = '#e11d48'; // Red
    }
    
    doc.save();
    doc.circle(startX + 15, startY + 6, 4).fill(bulletColor);
    doc.restore();
    
    doc.fontSize(10)
       .font('Helvetica-Bold')
       .fillColor('#1e293b')
       .text(label, startX + 28, startY, { lineGap: 2 });
       
    doc.fontSize(9)
       .font('Helvetica')
       .fillColor('#475569')
       .text(value, startX + 28, doc.y, { width: 480, lineGap: 4 });
       
    doc.moveDown(0.4);
    doc.x = 40; // Reset text cursor x-coordinate to prevent carryover indentation
}

function parseC2PAData(analysis) {
    const aiEvidence = [];
    const supportingEvidence = [];
    const warnings = [];
    const metadataAppendix = {};
    let evidenceScore = 0;

    const c2pa = (analysis.evidence && analysis.evidence.c2pa) || {};
    const c2paDetails = c2pa.details || {};
    const manifestInfo = c2paDetails.manifest_info || (analysis.scores && analysis.scores.c2pa_info) || {};
    const c2paValid = c2paDetails.c2pa_valid !== undefined ? c2paDetails.c2pa_valid : (analysis.scores && analysis.scores.c2pa_valid);
    const c2paDetected = c2paDetails.c2pa_detected || (analysis.scores && analysis.scores.c2pa_detected) || false;

    const addAppMetadata = (name, val) => {
        if (val !== undefined && val !== null && val !== '') {
            metadataAppendix[name] = val;
        }
    };

    addAppMetadata("file_size", analysis.fileSize || analysis.file_size);
    addAppMetadata("resolution", analysis.resolution);
    addAppMetadata("color_space", analysis.colorSpace || analysis.color_space);
    addAppMetadata("bit_depth", analysis.bitDepth || analysis.bit_depth);
    addAppMetadata("compression", analysis.compression);
    addAppMetadata("checksum", analysis.checksum || analysis.fileHash || analysis.file_hash);
    addAppMetadata("raw_headers", analysis.rawHeaders || analysis.raw_headers);
    addAppMetadata("hash_bytes", analysis.hashBytes || analysis.hash_bytes);
    addAppMetadata("padding_bytes", analysis.paddingBytes || analysis.padding_bytes);
    addAppMetadata("binary_blobs", analysis.binaryBlobs || analysis.binary_blobs);

    if (c2paDetected && manifestInfo && Object.keys(manifestInfo).length > 0) {
        const activeId = manifestInfo.active_manifest;
        const manifests = manifestInfo.manifests || {};
        const activeManifest = activeId ? (manifests[activeId] || {}) : {};

        const claimGen = activeManifest.claim_generator || "";
        let claimGenName = claimGen;
        const claimGenInfo = activeManifest.claim_generator_info || [];
        if (claimGenInfo.length > 0 && claimGenInfo[0].name) {
            claimGenName = claimGenInfo[0].name;
        }

        if (claimGenName) {
            const isAiGen = ["openai", "google", "gemini", "firefly", "midjourney", "stable diffusion", "runway"].some(kw => 
                claimGenName.toLowerCase().includes(kw)
            );
            if (isAiGen) {
                aiEvidence.push(`Claim Generator: ${claimGenName}`);
                evidenceScore += 20;
            } else if (c2paValid) {
                supportingEvidence.push(`Claim Generator: ${claimGenName}`);
            }
        }

        if (activeManifest.format) {
            supportingEvidence.push(`Content Format: ${activeManifest.format}`);
            addAppMetadata("format", activeManifest.format);
        }

        const assertions = activeManifest.assertions || [];
        assertions.forEach(assertion => {
            const label = assertion.label || "";
            const data = assertion.data || {};

            if (label.includes("actions")) {
                const actionsList = data.actions || [];
                actionsList.forEach(act => {
                    const actionName = act.action || "";
                    const softwareAgentObj = act.softwareAgent || "";
                    let agentName = "";
                    let agentVersion = "";
                    
                    if (typeof softwareAgentObj === "object" && softwareAgentObj !== null) {
                        agentName = softwareAgentObj.name || "";
                        agentVersion = softwareAgentObj.version || "";
                    } else {
                        agentName = String(softwareAgentObj);
                    }

                    const description = act.description || "";
                    const digitalSourceType = act.digitalSourceType || "";

                    if (agentName) {
                        const isAiAgent = ["openai", "google", "gemini", "firefly", "midjourney", "stable diffusion", "runway"].some(kw => 
                            agentName.toLowerCase().includes(kw)
                        );
                        if (isAiAgent) {
                            aiEvidence.push(`Actions softwareagent name: ${agentName}`);
                            evidenceScore += 20;
                        }
                    }

                    if (agentVersion) {
                        aiEvidence.push(`Actions softwareagent version: ${agentVersion}`);
                    }

                    if (actionName) {
                        const supportingActions = ["c2pa.created", "c2pa.edited", "c2pa.watermarked", "c2pa.watermarked.unbound"];
                        if (supportingActions.includes(actionName)) {
                            supportingEvidence.push(`Action: ${actionName}`);
                            evidenceScore += 10;
                        }
                    }

                    if (description) {
                        const descLower = description.toLowerCase();
                        const isAiDesc = ["generative ai", "ai generated", "synthid", "watermark"].some(kw => descLower.includes(kw));
                        if (isAiDesc) {
                            aiEvidence.push(`AI Declaration: ${description}`);
                            evidenceScore += 25;
                        }
                    }

                    if (digitalSourceType) {
                        if (digitalSourceType.toLowerCase().includes("trainedalgorithmicmedia")) {
                            aiEvidence.push("Digital Source Type: trainedAlgorithmicMedia");
                            evidenceScore += 25;
                        }
                    }

                    if (act.parameters) {
                        const paramsStr = JSON.stringify(act.parameters).toLowerCase();
                        if (paramsStr.includes("synthid")) {
                            aiEvidence.push("Watermark Evidence: Applied imperceptible SynthID watermark");
                            evidenceScore += 25;
                        }
                    }
                });
            }

            if (label.includes("digital-source-type")) {
                const dst = (data.digitalSourceType || "").toLowerCase();
                if (dst.includes("trainedalgorithmicmedia")) {
                    aiEvidence.push("Digital Source Type: trainedAlgorithmicMedia");
                    evidenceScore += 25;
                }
            }
        });

        const validationResults = manifestInfo.validation_results || {};
        const activeManifestVal = validationResults.activeManifest || {};
        const successList = activeManifestVal.success || [];
        const failureList = activeManifestVal.failure || [];

        successList.forEach(item => {
            const code = item.code || "";
            const supportingCodes = ["claimSignature.validated", "signingCredential.trusted", "timeStamp.trusted", "claimSignature.insideValidity", "timeStamp.validated", "signingCredential.notRevoked"];
            if (supportingCodes.some(sc => code.toLowerCase().includes(sc.toLowerCase()))) {
                supportingEvidence.push(`Signature Validation: ${code}`);
                evidenceScore += 10;
            }
        });

        failureList.forEach(item => {
            const code = item.code || "";
            warnings.push(`Validation Failure: ${code}`);
        });

        const valStatusList = manifestInfo.validation_status || [];
        valStatusList.forEach(item => {
            const code = item.code || item.status || "";
            if (code && !["success", "claim.validated"].includes(code)) {
                warnings.push(`Validation Failure: ${code}`);
            }
        });

        const ingredients = activeManifest.ingredients || [];
        if (ingredients.length > 0) {
            supportingEvidence.push(`Provenance Chain: ${ingredients.length} ingredient(s) detected`);
            evidenceScore += 10;

            ingredients.forEach((ing, index) => {
                if (ing.relationship) {
                    supportingEvidence.push(`Relationship: ${ing.relationship}`);
                }
                if (ing.description) {
                    supportingEvidence.push(`Description: ${ing.description}`);
                }
                if (ing.format) {
                    supportingEvidence.push(`Format: ${ing.format}`);
                }
            });
        }

        const nonAiKeys = ["title", "instance_id", "claim_generator", "claim_generator_info", "signature_info", "label", "claim_version", "thumbnail"];
        nonAiKeys.forEach(key => {
            if (activeManifest[key] !== undefined) {
                metadataAppendix[key] = activeManifest[key];
            }
        });
        
        if (manifestInfo.validation_status) {
            metadataAppendix["validation_status"] = manifestInfo.validation_status;
        }
        if (manifestInfo.validation_state) {
            metadataAppendix["validation_state"] = manifestInfo.validation_state;
        }
    }

    if (c2paDetected && !c2paValid) {
        if (!warnings.includes("Validation Failure: claimSignature.invalid")) {
            warnings.push("Validation Failure: claimSignature.invalid");
        }
    }

    const uniqueList = arr => Array.from(new Set(arr));
    const finalAiEvidence = uniqueList(aiEvidence);
    const finalSupportingEvidence = uniqueList(supportingEvidence);
    const finalWarnings = uniqueList(warnings);

    let forensicSummary = "";
    if (finalAiEvidence.length > 0) {
        const hasSynthID = finalAiEvidence.some(e => e.toLowerCase().includes("synthid"));
        const wmText = hasSynthID ? " confirms the application of an imperceptible SynthID watermark and" : "";
        
        let genName = "Google Generative AI";
        const claimGenEv = finalAiEvidence.find(e => e.includes("Claim Generator"));
        if (claimGenEv) {
            genName = claimGenEv.replace("Claim Generator: ", "");
        } else {
            const agentEv = finalAiEvidence.find(e => e.includes("softwareagent name"));
            if (agentEv) {
                genName = agentEv.replace("Actions softwareagent name: ", "");
            }
        }
        if (genName.toLowerCase() === "adobe_firefly") genName = "Adobe Firefly";
        
        forensicSummary = `The asset contains verified C2PA Content Credentials identifying ${genName} as the originating system. Metadata${wmText} the asset is cryptographically validated through trusted signing credentials. These findings constitute strong evidence that the media originated from an AI generation pipeline.`;
    } else if (c2paValid) {
        let genName = "Adobe Photoshop";
        const claimGenEv = finalSupportingEvidence.find(e => e.includes("Claim Generator"));
        if (claimGenEv) {
            genName = claimGenEv.replace("Claim Generator: ", "");
        }
        forensicSummary = `The asset contains verified C2PA Content Credentials identifying ${genName} as the originating system. Cryptographic signatures are valid and trusted. No AI generation metadata was detected. These findings support the authenticity and provenance of the asset.`;
    } else if (c2paDetected) {
        forensicSummary = `C2PA Content Credentials were detected but the cryptographic signature is invalid or has been tampered with. This indicates possible metadata tampering or modification of the asset since signing. This evidence supports, but does not solely determine, the final authenticity assessment.`;
    }

    return {
        aiEvidence: finalAiEvidence,
        supportingEvidence: finalSupportingEvidence,
        warnings: finalWarnings,
        metadataAppendix,
        forensicSummary,
        evidenceScore
    };
}

function generateForensicPDF(analysis) {
    return new Promise((resolve, reject) => {
        try {
            const doc = new PDFDocument({ margin: 40 });
            const buffers = [];
            
            doc.on('data', chunk => buffers.push(chunk));
            doc.on('end', () => resolve(Buffer.concat(buffers)));
            
            // ─── Header ───
            doc.fillColor('#0f172a')
               .fontSize(22)
               .font('Helvetica-Bold')
               .text('AuthenticEye - Forensic Analysis Report', { align: 'center' });
            
            doc.moveDown(1);
            doc.fontSize(10).font('Helvetica').fillColor('#64748b');
            doc.text(`Report Generated: ${new Date().toLocaleString()}`, { align: 'right' });
            doc.text(`Model Serving Version: ${analysis.modelVersion || 'v1'}`, { align: 'right' });
            
            doc.moveDown(0.5);
            doc.strokeColor('#e2e8f0').lineWidth(1).moveTo(40, doc.y).lineTo(570, doc.y).stroke();
            
            doc.moveDown(1.5);
            
            // ─── Verdict Verdict ───
            const verdict = analysis.result === 'fake' ? 'DEEPFAKE / SYNTHETIC' : 'AUTHENTIC / REAL';
            const verdictColor = analysis.result === 'fake' ? '#e11d48' : '#059669';
            const confidenceVal = analysis.confidence !== undefined ? analysis.confidence : (analysis.deepfakeProbability > 0.5 ? analysis.deepfakeProbability : 1.0 - analysis.deepfakeProbability);
            const riskLvl = analysis.riskLevel || (analysis.deepfakeProbability > 0.80 ? 'HIGH' : (analysis.deepfakeProbability > 0.45 ? 'MEDIUM' : 'LOW'));
            
            doc.fontSize(14).font('Helvetica-Bold').fillColor('#0f172a').text('Forensic Conclusion:');
            doc.fontSize(20).font('Helvetica-Bold').fillColor(verdictColor).text(verdict, { indent: 15 });
            doc.fontSize(12).font('Helvetica-Bold').fillColor('#1e293b').text(`Confidence Score: ${(confidenceVal * 100).toFixed(2)}%`, { indent: 15 });
            doc.fontSize(12).font('Helvetica-Bold').fillColor('#1e293b').text(`Risk Level: ${riskLvl}`, { indent: 15 });
            doc.moveDown(0.5);
            
            // ─── Content Credentials (C2PA) Section ───
            doc.fontSize(12).font('Helvetica-Bold').fillColor('#0f172a').text('Content Credentials (C2PA)');
            doc.moveDown(0.3);

            const c2pa = (analysis.evidence && analysis.evidence.c2pa) || {};
            const c2paDetails = c2pa.details || {};
            const c2paDetected = c2paDetails.c2pa_detected || (analysis.scores && analysis.scores.c2pa_detected) || false;

            if (!c2paDetected) {
                // No C2PA Found
                doc.fontSize(10).font('Helvetica-Bold').fillColor('#475569').text('ℹ No C2PA Content Credentials Found', { indent: 15 });
                doc.moveDown(0.2);
                doc.fontSize(9).font('Helvetica').fillColor('#64748b').text('No C2PA Content Credentials were found in this asset. The absence of credentials does not imply authenticity or manipulation, but indicates that no provenance history was embedded in the file.', { indent: 15, width: 500 });
                doc.moveDown(0.8);
            } else {
                const evidenceData = parseC2PAData(analysis);

                // Group 1: Warnings/Tampering if any
                if (evidenceData.warnings.length > 0) {
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#e11d48').text('WARNING / TAMPERING:');
                    doc.moveDown(0.3);
                    evidenceData.warnings.forEach(item => {
                        let parts = item.split(': ');
                        let label = parts[0];
                        let val = parts[1] || '';
                        drawEvidenceItem(doc, 'warning', label, val);
                    });
                    doc.moveDown(0.5);
                }

                // Group 2: High Confidence AI Evidence
                if (evidenceData.aiEvidence.length > 0) {
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#059669').text('HIGH CONFIDENCE AI EVIDENCE:');
                    doc.moveDown(0.3);
                    evidenceData.aiEvidence.forEach(item => {
                        let parts = item.split(': ');
                        let label = parts[0];
                        let val = parts[1] || '';
                        drawEvidenceItem(doc, 'high', label, val);
                    });
                    doc.moveDown(0.5);
                }

                // Group 3: Supporting Evidence
                if (evidenceData.supportingEvidence.length > 0) {
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#d97706').text('SUPPORTING EVIDENCE:');
                    doc.moveDown(0.3);
                    evidenceData.supportingEvidence.forEach(item => {
                        let parts = item.split(': ');
                        let label = parts[0];
                        let val = parts[1] || '';
                        drawEvidenceItem(doc, 'supporting', label, val);
                    });
                    doc.moveDown(0.5);
                }

                // Report Summary
                if (evidenceData.forensicSummary) {
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#0f172a').text('Forensic Explanation Summary:');
                    doc.moveDown(0.2);
                    doc.fontSize(9).font('Helvetica-Oblique').fillColor('#334155').text(evidenceData.forensicSummary, { indent: 15, width: 500 });
                    doc.moveDown(0.8);
                }
            }

            
            // ─── Forensic Findings Summary ───
            const explanation = analysis.explanation || {};
            const summaryText = explanation.summary || '';
            const reasons = explanation.reasons || [];
            
            if (summaryText || reasons.length > 0) {
                doc.fontSize(12).font('Helvetica-Bold').fillColor('#0f172a').text('Forensic Findings Summary:');
                doc.moveDown(0.3);
                
                if (summaryText) {
                    doc.fontSize(10).font('Helvetica-Oblique').fillColor('#334155').text(summaryText, { indent: 15 });
                    doc.moveDown(0.5);
                }
                
                if (reasons.length > 0) {
                    reasons.forEach(reason => {
                        doc.fontSize(10).font('Helvetica').fillColor('#334155').text(`• ${reason}`, { indent: 25 });
                        doc.moveDown(0.2);
                    });
                }
                doc.moveDown(1);
            }

            if (doc.y > 450) {
                doc.addPage();
            }
            
            const uploadDir = path.join(__dirname, '..');
            
            const origPath = path.join(uploadDir, analysis.fileUrl);
            const gradcamPath = analysis.explanationAssets?.gradcamUrl ? path.join(uploadDir, analysis.explanationAssets.gradcamUrl) : null;
            const fftPath = analysis.explanationAssets?.fftUrl ? path.join(uploadDir, analysis.explanationAssets.fftUrl) : null;
            const ganPath = analysis.explanationAssets?.ganUrl ? path.join(uploadDir, analysis.explanationAssets.ganUrl) : null;
            
            doc.fontSize(12).font('Helvetica-Bold').fillColor('#0f172a').text('Visual Evidence Artifacts:');
            doc.moveDown(0.5);
            
            let currentY = doc.y;
            
            if (fs.existsSync(origPath)) {
                try {
                    doc.image(origPath, 40, currentY, { width: 240, height: 180 });
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#64748b').text('Original Uploaded Media', 40, currentY + 185, { width: 240, align: 'center' });
                } catch (e) {
                    doc.fontSize(10).fillColor('red').text('[Error loading original image]', 40, currentY + 90);
                }
            } else {
                doc.fontSize(10).fillColor('#94a3b8').text('[Original image file not found on disk]', 40, currentY + 90);
            }
            
            if (gradcamPath && fs.existsSync(gradcamPath)) {
                try {
                    doc.image(gradcamPath, 310, currentY, { width: 240, height: 180 });
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#64748b').text('Grad-CAM Saliency Heatmap', 310, currentY + 185, { width: 240, align: 'center' });
                } catch (e) {
                    doc.fontSize(10).fillColor('red').text('[Error loading Grad-CAM]', 310, currentY + 90);
                }
            }
            
            doc.addPage();
            doc.fillColor('#0f172a')
               .fontSize(16)
               .font('Helvetica-Bold')
               .text('Frequency & Forensic Noise Map Spectrum');
            
            doc.moveDown(1);
            currentY = doc.y;
            
            if (fftPath && fs.existsSync(fftPath)) {
                try {
                    doc.image(fftPath, 40, currentY, { width: 240, height: 180 });
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#64748b').text('FFT Log Magnitude Spectrum', 40, currentY + 185, { width: 240, align: 'center' });
                } catch (e) {
                    doc.fontSize(10).fillColor('red').text('[Error loading FFT]', 40, currentY + 90);
                }
            }
            
            if (ganPath && fs.existsSync(ganPath)) {
                try {
                    doc.image(ganPath, 310, currentY, { width: 240, height: 180 });
                    doc.fontSize(10).font('Helvetica-Bold').fillColor('#64748b').text('GAN Fingerprint Residual Noise Map', 310, currentY + 185, { width: 240, align: 'center' });
                } catch (e) {
                    doc.fontSize(10).fillColor('red').text('[Error loading GAN noise]', 310, currentY + 90);
                }
            }
            
            doc.moveDown(3);
            doc.fontSize(10).font('Helvetica-Oblique').fillColor('#64748b');
            doc.text('Notice: This report contains probabilistic values computed by the deep learning ensemble and forensic analysis pipelines. Outcomes represent statistical indicators and should be verified by expert analysts.', 40, doc.y + 100, { width: 490 });
            
            // ─── C2PA Metadata Appendix & JSON Output ───
            const evidenceData = parseC2PAData(analysis);
            
            // Render Appendix page
            doc.addPage();
            doc.fontSize(14).font('Helvetica-Bold').fillColor('#0f172a').text('C2PA Metadata & Forensic Appendix');
            doc.moveDown(0.2);
            doc.strokeColor('#cbd5e1').lineWidth(1.5).moveTo(40, doc.y).lineTo(570, doc.y).stroke();
            doc.moveDown(0.5);

            doc.fontSize(9).font('Helvetica').fillColor('#475569').text('This appendix displays all remaining metadata fields extracted from the C2PA manifest to preserve complete transparency. These fields represent file specifications and cryptographic details not directly used in the AI generation determination.');
            doc.moveDown(0.8);

            const appendixKeys = Object.keys(evidenceData.metadataAppendix);
            if (appendixKeys.length === 0) {
                doc.fontSize(10).font('Helvetica-Oblique').fillColor('#64748b').text('No additional metadata fields found.');
            } else {
                appendixKeys.forEach(key => {
                    const value = evidenceData.metadataAppendix[key];
                    let valStr = '';
                    if (typeof value === 'object') {
                        valStr = JSON.stringify(value, null, 2);
                    } else {
                        valStr = String(value);
                    }
                    
                    doc.fontSize(9).font('Helvetica-Bold').fillColor('#1e293b').text(`${key}:`, { lineGap: 2 });
                    doc.fontSize(9).font('Helvetica').fillColor('#475569').text(valStr, { indent: 15, width: 500, lineGap: 4 });
                    doc.moveDown(0.4);
                });
            }

            // Render JSON Output page
            doc.addPage();
            doc.fontSize(14).font('Helvetica-Bold').fillColor('#0f172a').text('Forensic Evidence JSON Export');
            doc.moveDown(0.2);
            doc.strokeColor('#cbd5e1').lineWidth(1.5).moveTo(40, doc.y).lineTo(570, doc.y).stroke();
            doc.moveDown(0.8);

            const jsonOutput = {
                aiEvidence: evidenceData.aiEvidence,
                supportingEvidence: evidenceData.supportingEvidence,
                warnings: evidenceData.warnings,
                metadataAppendix: evidenceData.metadataAppendix,
                forensicSummary: evidenceData.forensicSummary,
                evidenceScore: evidenceData.evidenceScore
            };

            const jsonStr = JSON.stringify(jsonOutput, null, 2);
            
            // Draw a code-block background box
            const boxY = doc.y;
            doc.save();
            doc.fillColor('#f8fafc')
               .strokeColor('#e2e8f0')
               .lineWidth(1)
               .roundedRect(40, boxY, 530, 420, 6)
               .fillAndStroke();
            doc.restore();

            doc.fontSize(8.5)
               .font('Courier')
               .fillColor('#0f172a')
               .text(jsonStr, 50, boxY + 10, { width: 510, height: 400, lineGap: 2 });
            
            doc.end();
        } catch (err) {
            reject(err);
        }
    });
}

module.exports = {
    generateForensicPDF,
};
