package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"

	"github.com/hyperledger/fabric-gateway/pkg/client"
)

// Request body for StoreCertificate
type StoreCertRequest struct {
	CertID        string `json:"certID"`
	SHA256Hash    string `json:"sha256Hash"`
	FileName      string `json:"fileName"`
	Timestamp     string `json:"timestamp"`
	PhoneVerified string `json:"phoneVerified"`
	IncidentType  string `json:"incidentType"`
	Location      string `json:"location"`
}

// Standard API response
type APIResponse struct {
	Success bool        `json:"success"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
}

func serve(contract *client.Contract) {
	// CORS middleware wrapper
	withCORS := func(h http.HandlerFunc) http.HandlerFunc {
		return func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			w.Header().Set("Content-Type", "application/json")
			if r.Method == http.MethodOptions {
				w.WriteHeader(http.StatusOK)
				return
			}
			h(w, r)
		}
	}

	http.HandleFunc("/store",  withCORS(storeCertHandler(contract)))
	http.HandleFunc("/query",  withCORS(queryCertHandler(contract)))
	http.HandleFunc("/verify", withCORS(verifyCertHandler(contract)))
	http.HandleFunc("/health", withCORS(healthHandler))

	if err := http.ListenAndServe(":8080", nil); err != nil {
		log.Fatalf("Server failed: %v", err)
	}
}

// POST /store
// Body: { certID, sha256Hash, fileName, timestamp, phoneVerified, incidentType, location }
func storeCertHandler(contract *client.Contract) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			writeError(w, http.StatusMethodNotAllowed, "POST only")
			return
		}

		body, err := io.ReadAll(r.Body)
		if err != nil {
			writeError(w, http.StatusBadRequest, "Failed to read body")
			return
		}

		var req StoreCertRequest
		if err = json.Unmarshal(body, &req); err != nil {
			writeError(w, http.StatusBadRequest, "Invalid JSON: "+err.Error())
			return
		}

		// Validate required fields
		if req.CertID == "" || req.SHA256Hash == "" || req.FileName == "" {
			writeError(w, http.StatusBadRequest, "certID, sha256Hash and fileName are required")
			return
		}

		_, err = contract.SubmitTransaction(
			"StoreCertificate",
			req.CertID,
			req.SHA256Hash,
			req.FileName,
			req.Timestamp,
			req.PhoneVerified,
			req.IncidentType,
			req.Location,
		)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "Chaincode error: "+err.Error())
			return
		}

		writeSuccess(w, fmt.Sprintf("Certificate %s stored on ledger", req.CertID), nil)
	}
}

// GET /query?certID=CERT001
func queryCertHandler(contract *client.Contract) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "GET only")
			return
		}

		certID := r.URL.Query().Get("certID")
		if certID == "" {
			writeError(w, http.StatusBadRequest, "certID query param required")
			return
		}

		result, err := contract.EvaluateTransaction("QueryCertificate", certID)
		if err != nil {
			writeError(w, http.StatusNotFound, "Chaincode error: "+err.Error())
			return
		}

		// Parse ledger JSON and return it as data
		var certData map[string]interface{}
		json.Unmarshal(result, &certData)
		writeSuccess(w, "Certificate found", certData)
	}
}

// GET /verify?certID=CERT001&sha256Hash=abc123...
func verifyCertHandler(contract *client.Contract) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			writeError(w, http.StatusMethodNotAllowed, "GET only")
			return
		}

		certID     := r.URL.Query().Get("certID")
		sha256Hash := r.URL.Query().Get("sha256Hash")
		if certID == "" || sha256Hash == "" {
			writeError(w, http.StatusBadRequest, "certID and sha256Hash are required")
			return
		}

		result, err := contract.EvaluateTransaction("VerifyCertificate", certID, sha256Hash)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "Chaincode error: "+err.Error())
			return
		}

		verdict := string(result)
		isVerified := len(verdict) > 0 && verdict[:8] == "VERIFIED"
		writeSuccess(w, verdict, map[string]bool{"verified": isVerified})
	}
}

// GET /health
func healthHandler(w http.ResponseWriter, r *http.Request) {
	writeSuccess(w, "NyayaSetu Fabric REST API is running", nil)
}

func writeSuccess(w http.ResponseWriter, message string, data interface{}) {
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(APIResponse{Success: true, Message: message, Data: data})
}

func writeError(w http.ResponseWriter, status int, message string) {
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(APIResponse{Success: false, Message: message})
}
