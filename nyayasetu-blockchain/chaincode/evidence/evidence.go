package main

import (
	"encoding/json"
	"fmt"
	"log"

	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

// SmartContract provides functions for managing BSA Section 63 evidence certificates
type SmartContract struct {
	contractapi.Contract
}

// EvidenceCertificate is the asset stored on the ledger for every certificate generated
type EvidenceCertificate struct {
	DocType       string `json:"docType"`       // always "evidence_certificate"
	CertID        string `json:"certID"`        // unique ID — same as PDF filename (without .pdf)
	SHA256Hash    string `json:"sha256Hash"`    // SHA-256 of the original evidence file
	FileName      string `json:"fileName"`      // original uploaded file name
	Timestamp     string `json:"timestamp"`     // when the certificate was generated (ISO8601)
	PhoneVerified string `json:"phoneVerified"` // masked phone number e.g. +91****7890
	IncidentType  string `json:"incidentType"`  // e.g. "Theft", "Assault", "Fraud"
	Location      string `json:"location"`      // GPS or address from EXIF / user input
	IssuedBy      string `json:"issuedBy"`      // always "NyayaSetu BSA Section 63"
	TxTimestamp   string `json:"txTimestamp"`   // Fabric ledger transaction timestamp
}

const certDocType = "evidence_certificate"

// -------------------------------------------------------------------
// StoreCertificate — called by NyayaSetu backend after PDF is generated
// -------------------------------------------------------------------
func (s *SmartContract) StoreCertificate(
	ctx contractapi.TransactionContextInterface,
	certID string,
	sha256Hash string,
	fileName string,
	timestamp string,
	phoneVerified string,
	incidentType string,
	location string,
) error {
	// 1. Prevent duplicate certificate IDs
	exists, err := s.certExists(ctx, certID)
	if err != nil {
		return err
	}
	if exists {
		return fmt.Errorf("certificate with ID %s already exists on the ledger", certID)
	}

	// 2. Get Fabric transaction timestamp (immutable, set by orderer)
	txTimestamp, err := ctx.GetStub().GetTxTimestamp()
	if err != nil {
		return fmt.Errorf("failed to get transaction timestamp: %w", err)
	}

	// 3. Build the asset
	cert := EvidenceCertificate{
		DocType:       certDocType,
		CertID:        certID,
		SHA256Hash:    sha256Hash,
		FileName:      fileName,
		Timestamp:     timestamp,
		PhoneVerified: phoneVerified,
		IncidentType:  incidentType,
		Location:      location,
		IssuedBy:      "NyayaSetu BSA Section 63",
		TxTimestamp:   txTimestamp.String(),
	}

	// 4. Marshal to JSON and write to ledger
	certJSON, err := json.Marshal(cert)
	if err != nil {
		return fmt.Errorf("failed to marshal certificate: %w", err)
	}

	return ctx.GetStub().PutState(certID, certJSON)
}

// -------------------------------------------------------------------
// QueryCertificate — returns full certificate details for a given certID
// -------------------------------------------------------------------
func (s *SmartContract) QueryCertificate(
	ctx contractapi.TransactionContextInterface,
	certID string,
) (*EvidenceCertificate, error) {
	certJSON, err := ctx.GetStub().GetState(certID)
	if err != nil {
		return nil, fmt.Errorf("failed to read ledger: %w", err)
	}
	if certJSON == nil {
		return nil, fmt.Errorf("certificate %s not found on ledger", certID)
	}

	var cert EvidenceCertificate
	if err = json.Unmarshal(certJSON, &cert); err != nil {
		return nil, fmt.Errorf("failed to unmarshal certificate: %w", err)
	}

	// Ensure we are reading the right docType
	if cert.DocType != certDocType {
		return nil, fmt.Errorf("asset %s is not an evidence certificate", certID)
	}

	return &cert, nil
}

// -------------------------------------------------------------------
// VerifyCertificate — verifies that a given SHA-256 hash matches what
// is stored on the ledger for a certID. Returns a plain-English verdict.
// -------------------------------------------------------------------
func (s *SmartContract) VerifyCertificate(
	ctx contractapi.TransactionContextInterface,
	certID string,
	sha256Hash string,
) (string, error) {
	cert, err := s.QueryCertificate(ctx, certID)
	if err != nil {
		return "", err
	}

	if cert.SHA256Hash == sha256Hash {
		return fmt.Sprintf(
			"VERIFIED: Certificate %s is authentic. SHA-256 hash matches ledger record. Stored on %s.",
			certID, cert.TxTimestamp,
		), nil
	}

	return fmt.Sprintf(
		"TAMPERED: Certificate %s hash does NOT match ledger. Evidence may have been modified.",
		certID,
	), nil
}

// -------------------------------------------------------------------
// certExists — internal helper (lowercase = not exposed as chaincode fn)
// -------------------------------------------------------------------
func (s *SmartContract) certExists(
	ctx contractapi.TransactionContextInterface,
	certID string,
) (bool, error) {
	certJSON, err := ctx.GetStub().GetState(certID)
	if err != nil {
		return false, fmt.Errorf("failed to read world state: %w", err)
	}
	return certJSON != nil, nil
}

// -------------------------------------------------------------------
// main — entry point, same pattern as your farmer insurance chaincode
// -------------------------------------------------------------------
func main() {
	chaincode, err := contractapi.NewChaincode(&SmartContract{})
	if err != nil {
		log.Panicf("Error creating NyayaSetu evidence chaincode: %v", err)
	}

	if err := chaincode.Start(); err != nil {
		log.Panicf("Error starting NyayaSetu evidence chaincode: %v", err)
	}
}
