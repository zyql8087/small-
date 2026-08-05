function code = map_m04_failure_code(identifier)
%MAP_M04_FAILURE_CODE Map stable MATLAB identifiers to the M04 public API.

    identifier = validate_text_scalar(identifier, 'identifier', ...
        'MATLABGyroid:DescriptorContractMismatch');
    if strcmp(identifier, 'MATLABGyroid:M03ArtifactMismatch') || ...
            strcmp(identifier, 'MATLABGyroid:STLVerificationError')
        code = 'M03_ARTIFACT_MISMATCH';
    elseif strcmp(identifier, 'MATLABGyroid:DescriptorDependencyMissing')
        code = 'DESCRIPTOR_DEPENDENCY_MISSING';
    elseif strcmp(identifier, 'MATLABGyroid:DescriptorContractMismatch')
        code = 'DESCRIPTOR_CONTRACT_MISMATCH';
    elseif strcmp(identifier, 'MATLABGyroid:DescriptorNonfinite')
        code = 'DESCRIPTOR_NONFINITE';
    elseif strcmp(identifier, 'MATLABGyroid:DescriptorProfileInvalid')
        code = 'DESCRIPTOR_PROFILE_INVALID';
    elseif strcmp(identifier, 'MATLABGyroid:M04ScaleNotIdentified')
        code = 'M04_SCALE_NOT_IDENTIFIED';
    elseif strcmp(identifier, 'MATLABGyroid:M04Gate0NotFrozen')
        code = 'M04_GATE0_NOT_FROZEN';
    elseif strcmp(identifier, 'MATLABGyroid:M04Gate0Failed')
        code = 'M04_GATE0_FAILED';
    elseif strcmp(identifier, 'MATLABGyroid:OutputConflict')
        code = 'OUTPUT_CONFLICT';
    elseif startsWith(identifier, 'MATLABGyroid:Invalid') || ...
            strcmp(identifier, 'MATLABGyroid:MethodConstraint') || ...
            strcmp(identifier, 'MATLABGyroid:OutOfBounds')
        code = 'DESCRIPTOR_CONTRACT_MISMATCH';
    else
        code = 'INTERNAL_ERROR';
    end
end
