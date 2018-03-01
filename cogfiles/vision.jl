using Combinatorics
using CDDLib, Polyhedra

function coefficients(n_max)

    function count(order)
        vision_num = 0
        highest_seen = 0
        for i in order
            if i > highest_seen
                highest_seen = i
                vision_num = vision_num + 1
            end
        end
        return vision_num
    end

    function build_num_dict(print_dict)
        vision_nums = Dict()
        perms = collect(permutations(1:n_max))

        for perm in perms
            perm = hcat(perm)'
            vision_num = count(perm)
            try
                current_val = vision_nums[vision_num]
                vision_nums[vision_num] = vcat(current_val, perm)
                catch error
                    if isa(error, KeyError)
                        vision_nums[vision_num] = perm
                    end
            end
        end
        if print_dict
            println(vision_nums)
            for key in sort(collect(keys(vision_nums)))
                println("$key => $(vision_nums[key])")
            end
        end
        return vision_nums
    end
    
    function build_ineqs_dict()
        vision_nums = build_num_dict(false)
        #= ineqs = Dict{Int64,Dict{String,Array{Any,Any}}} =#
        ineqs = Dict()
        for idx in 1:n_max
            #= idx_dict = Dict{String,Array{Any,Any}} =#
            idx_dict = Dict()
            denominators = Set([])
            vertices = vision_nums[idx]
            points = SimpleVRepresentation(vertices)
            poly = polyhedron(points, CDDLibrary(:exact))
            removehredundancy!(poly)
            ineq = SimpleHRepresentation(poly)
            ineqA = ineq.A
            ineqb = ineq.b
            lcmA = lcm(denominator.(ineqA))
            ineqA = convert.(Int64, lcmA*ineqA)
            ineqb = convert.(Int64, lcmA*ineqb)
            idx_dict["A"] = ineqA
            idx_dict["b"] = ineqb
            ineqs[idx] = idx_dict
        end
        return ineqs
    end

    return build_ineqs_dict()
end
